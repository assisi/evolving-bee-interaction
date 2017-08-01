#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import PIL.Image
import PIL.ImageChops
import subprocess
import time

import roi_picker
import util
import yaml
import zmq_sock_utils

CAMERA_RESOLUTION_X = 2048
CAMERA_RESOLUTION_Y = 2048

MAXIMUM_TEMPERATURE_DIFFERENCE = 1

ROI_DATA = 2
ROI_BACKGROUND = 0
ROI_PREVIOUS = 1

class BasicArena:
    """
    This class represents a basic arena with only the CASU workers and without regions of interest.
      The attributes of this class represent the ZMQ sockets
    where the worker programs are listening for commands.
    """
    def __init__ (self, dict_workers_stubs, casu_names, number_active_CASUs):
        """
        Ask the user the CASUs that are this arena, and the position of the arena in the background image.
        """
        self.list_workers_stubs = [BasicArena.__ask_casu_number_ (name, dict_workers_stubs) for name in casu_names]
        self.number_active_CASUs = number_active_CASUs
        self.selected_region_of_interest_index = 0

    def unselect_workers (self):
        """If the user does not like the arena, the workers that have been
        assigned are free to be selected again.
        """
        for ws in self.list_workers_stubs:
            ws.in_use = False

    def status (self):
        """
        Return the suitability of this arena to run a vibration pattern.  The
        CASU temperature must be below a minimum threshold.  The suitability is
        a function of the CASU ring temperature sensor.
        """
        import worker
        value = 0
        temps = []
        good = True
        for ws in self.list_workers_stubs:
            temperature = zmq_sock_utils.send_recv (ws.socket, [worker.CASU_STATUS])
            temps.append (temperature)
            if temperature > worker.CASU_TEMPERATURE + 1 or temperature < worker.CASU_TEMPERATURE - 1:
                good = False
            else:
                value += worker.CASU_TEMPERATURE + 1 - temperature
        if good:
            for i1 in xrange (len (self.list_workers_stubs) - 1):
                for i2 in xrange (i1, len (self.list_workers_stubs)):
                    if abs (temps [i1] - temps [i2]) > MAXIMUM_TEMPERATURE_DIFFERENCE:
                        good = False
        if not good:
            value = 0
        return (value, temps)
            

    def run_vibration_model (self, config, *parameters):
        """
        Pick a random worker and ask it to run the vibration pattern.
        Waits for the response from the selected worker.  Workers respond when they finish their role.
        """
        import worker
        for i in xrange (len (self.list_workers_stubs)):
            worker_stub = self.list_workers_stubs [i]
            if i == self.selected_region_of_interest_index or i < self.number_active_CASUs:
                zmq_sock_utils.send (worker_stub.socket, [worker.ACTIVE_CASU] + list (parameters))
            else:
                zmq_sock_utils.send (worker_stub.socket, [worker.PASSIVE_CASU])
        time_start_vibration_pattern = None
        for ws in self.list_workers_stubs:
            answer = zmq_sock_utils.recv (ws.socket)
            if len (answer) == 2:
                time_start_vibration_pattern = answer [1]
            print ("Worker responsible for casu #%d responded with: %s" % (ws.casu_number, str (answer)))
        return time_start_vibration_pattern

    @staticmethod
    def __ask_casu_number_ (name, dict_workers_stubs):
        """
        Ask the user the CASU number of a CASU with the given name relative to the background image.
        Returns a tuple with the casu number and the zmq socket.
        """
        while True:
            try:
                number = int (raw_input ("Number of %s CASU? " % name))
                if number in dict_workers_stubs:
                    if dict_workers_stubs [number].in_use:
                        print ("This CASU is already chosen!")
                    else:
                        dict_workers_stubs [number].in_use = True
                        return dict_workers_stubs [number]
                else:
                    print ("There is no worker associated with CASU number %d." % (number))
            except ValueError:
                print ("Invalid number")

diff_index = 1

class AbstractVideoTapeableArena (BasicArena):
    """
    An arena that can be video taped, that has regions of interest, and that has controllable CASUs.

    The file names of the video frames are tmp/iteration-frame-NNNN.jpg.
    """
    def __init__ (self, dict_workers_stubs, casu_names, number_active_CASUs, number_ROIs, episode_path, img_path, index, config):
        BasicArena.__init__ (self, dict_workers_stubs, casu_names, number_active_CASUs)
        self.episode_path = episode_path
        self.img_path = img_path
        self.index = index
        self.number_ROIs = number_ROIs
        self.same_colour_threshold = '%d%%' % (config.same_colour_threshold)
        self.same_colour_threshold_int = int (config.same_colour_threshold * 255 / 100)
        self.delta_frame = int (config.frames_per_second / config.interval_current_previous_frame)

    def __compare_frame_ImageMagick (self, mask, frame1, frame2):
        """
        Compare two frames using the convert program from the ImageMagick suite.  This program computes the pixel count difference between two frames in a region of interest.
        """
        command = [
            util.CONVERT_BIN_FILENAME,
            '(', mask, frame1, '-compose', 'multiply', '-composite', ')',
            '(', mask, frame2, '-compose', 'multiply', '-composite', ')',
            '-metric', 'AE', '-fuzz', self.same_colour_threshold, '-compare',
            '-format', '%[distortion]', 'info:'
            ]
        process = subprocess.Popen (command, stdout = subprocess.PIPE)
        out, err = process.communicate ()
        try:
            return int (out)
        except:
            print ("Result is [" + out + "]")
            raise

    def compare_frame_PIL (self, mask, frame1, frame2):
        """
        Compare two frames to see how many pixels are different in a specific region of interest.
        """
        def open_image (filename):
            result = PIL.Image.open (filename)
            if result.mode != 'L':
                result = result.convert (mode = 'L')
            return result
        img_mask = open_image (mask)
        img_frame1 = open_image (frame1)
        img_frame2 = open_image (frame2)
        img_roi1 = PIL.ImageChops.multiply (img_mask, img_frame1)
        img_roi2 = PIL.ImageChops.multiply (img_mask, img_frame2)
        img_diff = PIL.ImageChops.difference (img_roi1, img_roi2)
        global diff_index
        img_diff.save ('diff-%04d.png' % (diff_index))
        diff_index += 1
        histogram = img_diff.histogram ()
        return sum (histogram [self.same_colour_threshold_int:256])

    def compare_frames (self, ith_frame):
        """
        Compare the background frame with the ith frame from an iteration video
        and compare frames that are delta_frame apart.
        Returns a list with number of pixels that are different,
        meaning the pixel value difference is higher than threshold.
        The contents of the list are:

        [
          pixel count difference background ith frame region-of-interest 1,
          pixel count difference frames delta_frame apart region-of-interest 1,
          pixel count difference background ith frame region-of-interest 2,
          pixel count difference frames delta_frame apart region-of-interest 2,
          ...
        ]
        """
        frame1 = "tmp/iteration-frame-%04d.jpg" % ith_frame
        return [
            self.compare_frame_PIL (mask, frame1, frame2)
            if not frame2 is None
            else -1
            for index in xrange (self.number_ROIs)
            for mask in ["%sMask-%d.jpg" % (self.img_path, index)]
            for frame2 in [
                    "%sBackground.jpg" % (self.episode_path),
                    "tmp/iteration-frame-%04d.jpg" % (ith_frame - self.delta_frame)
                    if ith_frame > self.delta_frame
                    else None]
            ]



    def write_properties (self, list_casu_names):
        '''
        Save the CASU numbers.
        '''
        data = {}
        for a_worker_stub, a_casu_name in zip (self.list_workers_stubs, list_casu_names):
            data [a_casu_name] = a_worker_stub.casu_number
        with open (self.img_path + "casu.properties", 'w') as fp:
            yaml.dump (data, fp, default_flow_style = False)
            fp.close ()

class StadiumBorderArena (AbstractVideoTapeableArena):
    """
    An arena with two CASUs (top and bottom), stadium shape, and rectangular region of interest.
    """
    def __init__ (self, dict_workers_stubs, episode_path, img_path, index, config):
        """
        Ask the user the position of the arena border in the background frame.
        """
        AbstractVideoTapeableArena.__init__ (self, dict_workers_stubs, StadiumBorderArena.ROI_names (), 1, episode_path, img_path, index, config)
        ok = False
        while not ok:
            try:
                self.arena_left = int (raw_input ("Leftmost (min) pixel of the arena? "))
                self.arena_right = int (raw_input ("Rightmost (max) pixel of the arena? "))
                if self.arena_left > self.arena_right:
                    print ("Invalid pixel data!")
                    continue
                self.arena_top = int (raw_input ("Topmost (min) pixel of the arena? "))
                self.arena_bottom = int (raw_input ("Bottommost (max) pixel of the arena? "))
                if self.arena_top > self.arena_bottom:
                    print ("Invalid pixel data!")
                    continue
                self.arena_border_coordinate = int (raw_input ("Vertical coordinate of the border? "))
                if not (self.arena_top < self.arena_border_coordinate < self.arena_bottom):
                    print ("Invalid border position!")
                    continue
                ok = True
            except ValueError:
                print ("Not a number!")

    def create_region_of_interests_image (self):
        """
        Process the background frame and create an image with regions of interest highlighted.
        """
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            self.episode_path + 'Background.jpg',
            '-crop', str (self.arena_right - self.arena_left) + 'x' + str (self.arena_bottom - self.arena_top) + '+' + str (self.arena_left) + '+' + str (self.arena_top),
            '-fill', 'rgb(255,255,0)',
            '-tint', '100',
            'Measured-Area-tmp-2.jpg'])
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            self.episode_path + 'Background.jpg',
            '-draw', 'image SrcOver %d,%d %d,%d Measured-Area-tmp-2.jpg' % (self.arena_left, self.arena_top,  self.arena_right - self.arena_left, self.arena_bottom - self.arena_top),
            'Measured-Area-tmp-3.jpg'])
        x0, y0 = self.arena_left,  self.arena_border_coordinate,
        x1, y1 = self.arena_right, self.arena_border_coordinate
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            'Measured-Area-tmp-3.jpg',
            '-fill', 'rgb(0,0,255)',
            '-draw', 'line %d,%d %d,%d' % (x0, y0, x1, y1),
            self.img_path + 'Region-of-Interests.jpg'])
        subprocess.call ([
            'rm',
            'Measured-Area-tmp-2.jpg',
            'Measured-Area-tmp-3.jpg'])

    def create_mask_images_casu_images (self, config):
        """
        Use the background to create the image masks and the casu images that are going to be used by the image processing functions.
        """
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            self.episode_path + 'Background.jpg',
            '-fill', 'rgb(0,0,0)',
            '-draw', 'rectangle 0,0 %d,%d' % (config.image_width, config.image_height),
            '-fill', 'rgb(255,255,255)',
            '-draw', 'rectangle %d,%d %d,%d' % (self.arena_left, self.arena_top, self.arena_right, self.arena_border_coordinate),
            self.img_path + 'Mask-0.jpg'])
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            self.episode_path + 'Background.jpg',
            '-fill', 'rgb(0,0,0)',
            '-draw', 'rectangle 0,0 %d,%d' % (config.image_width, config.image_height),
            '-fill', 'rgb(255,255,255)',
            '-draw', 'rectangle %d,%d %d,%d' % (self.arena_left, self.arena_border_coordinate, self.arena_right, self.arena_bottom),
            self.img_path + 'Mask-1.jpg'])
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            self.episode_path + 'Background.jpg',
            self.img_path + 'Mask-0.jpg',
            '-compose', 'multiply',
            '-composite',
            self.img_path + 'Arena-Top-CASU.jpg'])
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            self.episode_path + 'Background.jpg',
            self.img_path + 'Mask-1.jpg',
            '-compose', 'multiply',
            '-composite',
            self.img_path + 'Arena-Bot-CASU.jpg'])

    @staticmethod
    def image_processing_header ():
        return ["background_top", "previous_iteration_top", "background_bottom", "previous_iteration_bottom"]

    @staticmethod
    def number_ROIs ():
        return 2

    @staticmethod
    def number_CASUs ():
        return 2

    @staticmethod
    def ROI_names ():
        return ["top", "bottom"]

    @staticmethod
    def ROIs_presentation_order ():
        return [1, 0]

    @staticmethod
    def name ():
        return 'stadium'


class CircularArena (AbstractVideoTapeableArena):
    """
    A circular arena with a single casu.  Region of interest is circular
    """
    def __init__ (self, dict_workers_stubs, episode_path, img_path, index, config):
        """
        Ask the user the position of the arena, of the casu, and of the region of interest.
        """
        AbstractVideoTapeableArena.__init__ (self, dict_workers_stubs, CircularArena.ROI_names (), 1, CircularArena.number_ROIs (), episode_path, img_path, index, config)

    def create_region_of_interests_image (self):
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            self.episode_path + 'Background.jpg',
            '-fill', '#FFFF007F',
            '-draw', 'circle %d,%d %d,%d' % (self.arena_center_x, self.arena_center_y, self.arena_center_x, self.arena_center_y + self.arena_radius), 
            self.img_path + 'Region-of-Interests.jpg'])

    def create_mask_images_casu_images (self, config):
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            '-size', '%dx%d' % (config.image_width, config.image_height),
            'xc:black',
            '-fill', '#FFFFFF',
            '-draw', 'circle %d,%d %d,%d' % (self.arena_center_x, self.arena_center_y, self.arena_center_x, self.arena_center_y + self.arena_radius), 
            self.img_path + 'Mask-0.jpg'])

    @staticmethod
    def image_processing_header ():
        return ["background", "previous_iteration"]

    @staticmethod
    def number_ROIs ():
        return 1

    @staticmethod
    def number_CASUs ():
        return 1

    @staticmethod
    def ROI_names ():
        return ["center"]

    @staticmethod
    def ROIs_presentation_order ():
        return [0]

    @staticmethod
    def name ():
        return 'circular'

    ROI_PICKER = None

    @staticmethod
    def roi_picker ():
        if CircularArena.ROI_PICKER == None:
            CircularArena.ROI_PICKER = roi_picker.CircularArenaROIPicker (None)
        return CircularArena.ROI_PICKER

    def write_properties (self):
        """
        Save the arena properties for later reference.
        """
        AbstractVideoTapeableArena.write_properties (self, CircularArena.ROI_names ())

class TwoCircularArenas (AbstractVideoTapeableArena):
    '''
    An arena that contains two circular arenas, each one around a casu and with its own region of interest.
    '''
    def __init__ (self, dict_workers_stubs, episode_path, img_path, index, config):
        AbstractVideoTapeableArena.__init__ (self, dict_workers_stubs, TwoCircularArenas.ROI_names (), 1, TwoCircularArenas.number_ROIs (), episode_path, img_path, index, config)

    @staticmethod
    def image_processing_header ():
        return ["active_background", "active_previous_iteration", "passive_background", "passive_previous_iteration"]

    @staticmethod
    def number_ROIs ():
        return 2

    @staticmethod
    def number_CASUs ():
        return 2

    @staticmethod
    def ROI_names ():
        return ['active', 'passive']

    @staticmethod
    def ROIs_presentation_order ():
        return [0, 1]

    @staticmethod
    def name ():
        return 'two circular'

    ROI_PICKER = None

    @staticmethod
    def roi_picker ():
        if TwoCircularArenas.ROI_PICKER == None:
            TwoCircularArenas.ROI_PICKER = roi_picker.TwoCircularArenasROIPicker (None)
        return TwoCircularArenas.ROI_PICKER

    def write_properties (self):
        """
        Save the arena properties for later reference.
        """
        AbstractVideoTapeableArena.write_properties (self, TwoCircularArenas.ROI_names ())

class TwoBoxesArena (AbstractVideoTapeableArena):
    """
    An arena that contains two rectangular boxes that may not be adjacent.  Each box has a single CASUs.  Regions of interest are the boxes around the CASUs.
    """
    LABELS = ["first", "second"]
    def __init__ (self, worker_settings, episode_path, img_path, index, config):
        """
        Ask the user the position of the arena, of the casu, and of the region of interest.
        """
        AbstractVideoTapeableArena.__init__ (self, worker_settings, ["first", "second"], episode_path, img_path, index, config)
        self.roi_top = [-1, -1]
        self.roi_left = [-1, -1]
        self.roi_right = [-1, -1]
        self.roi_bottom = [-1, -1]
        for index in xrange (2):
            ok = False
            while not ok:
                try:
                    self.roi_left [index] = int (raw_input ("Leftmost (min) pixel of the %s box? " % (TwoBoxesArena.LABELS [index])))
                    self.roi_right [index] = int (raw_input ("Rightmost (max) pixel of the %s box? " % (TwoBoxesArena.LABELS [index])))
                    if self.roi_left [index] > self.roi_right [index]:
                        print ("Invalid pixel data!")
                        continue
                    self.roi_top [index] = int (raw_input ("Topmost (min) pixel of the %s box? " % (TwoBoxesArena.LABELS [index])))
                    self.roi_bottom [index] = int (raw_input ("Bottommost (max) pixel of the %s box? " % (TwoBoxesArena.LABELS [index])))
                    if self.roi_top [index] > self.roi_bottom [index]:
                        print ("Invalid pixel data!")
                        continue
                    ok = True
                except ValueError:
                    print ("Not a number!")

    def create_region_of_interests_image (self):
        subprocess.check_call ([
            util.CONVERT_BIN_FILENAME,
            self.episode_path + 'Background.jpg',
            '-fill', '#FFFF007F',
            '-draw', 'rectangle %d,%d %d,%d' % (self.roi_left [0], self.roi_top [0], self.roi_right [0], self.roi_bottom [0]),
            '-draw', 'rectangle %d,%d %d,%d' % (self.roi_left [1], self.roi_top [1], self.roi_right [1], self.roi_bottom [1]),
            self.img_path + 'Region-of-Interests.jpg'])

    def create_mask_images_casu_images (self, config):
        for index in xrange (2):
            subprocess.check_call ([
                CONVERT_BIN_FILENAME,
                '-size', '%dx%d' % (config.image_width, config.image_height),
                'xc:black',
                '-fill', '#FFFFFF',
                '-draw', 'rectangle %d,%d %d,%d' % (self.roi_left [index], self.roi_top [index], self.roi_right [index], self.roi_bottom [index]),
                self.img_path + 'Mask-%d.jpg' % (index)])

    def image_processing_header (self):
        return ["background_first", "previous_iteration_first", "background_second", "previous_iteration_second"]

    def write_properties (self):
        """
        Save the arena properties for later reference.
        """
        fp = open (self.img_path + "properties", 'w')
        for index, label in zip (xrange (2), TwoBoxesArena.LABELS):
            fp.write ("""roi_left_%s : %d
roi_right_%s : %d
roi_top_%s : %d
roi_bottom_%s : %d
""" % (label, self.roi_left [index],
       label, self.roi_right [index],
       label, self.roi_top [index],
       label, self.roi_bottom [index]))
        fp.close ()

class Corridor2Start2GoalArena (AbstractVideoTapeableArena):
    '''
    A corridor arena with 2 start zones and with 2 goal zones.
    Each goal zone has one active CASU. There can be any number
    of passive CASUs in between the two active CASUs.
    '''

    NUMBER_PASSIVE_CASUs = 1

    def __init__ (self, dict_workers_stubs, episode_path, img_path, index, config):
        AbstractVideoTapeableArena.__init__ (
            self,
            dict_workers_stubs,
            Corridor2Start2GoalArena.CASU_names (),
            number_active_CASUs = -1, # not used
            number_ROIs = -1, # not used
            episode_path = episode_path,
            img_path = img_path,
            index = index,
            config = config)

    def compare_frames_start_region (self, ith_frame):
        '''
        Specialisation of method AbstractVideoTapeableArena.compare_frames that focus on the start regions-of-interest.
        '''
        frame1 = "tmp/trial-%04d.jpg" % ith_frame
        return [
            self.compare_frame_PIL (mask, frame1, frame2)
            for mask in ["%sMask-%d.jpg" % (self.img_path, index) for index in roi_picker.Corridor2Start2GoalROIPicker.get_indexes_start_masks ()]
            for frame2 in ["%sBackground.jpg" % (self.episode_path)]
            ]

    def compare_frames_goal_region (self, ith_frame, index_goal):
        '''
        Specialisation of method AbstractVideoTapeableArena.compare_frames that focus on the start regions-of-interest.
        '''
        frame1 = "tmp/iteration-frame-%04d.jpg" % ith_frame
        return [
            self.compare_frame_PIL (mask, frame1, frame2)
            if not frame2 is None
            else -1
            for mask in ["%sMask-%d.jpg" % (self.img_path, roi_picker.Corridor2Start2GoalROIPicker.get_indexes_goal_masks () [index_goal])]
            for frame2 in [
                    "%sBackground.jpg" % (self.episode_path),
                    "tmp/iteration-frame-%04d.jpg" % (ith_frame - self.delta_frame)
                    if ith_frame > self.delta_frame
                    else None]
            ]

    def compare_frames (self, ith_frame):
        '''
        We only compare frames using the region of interest that corresponds to
        the selected region of interest, i.e., the one where there were more
        bees when the chromosome evaluation started. See method
        wait_for_bee_readiness of class BeesInStartROI.
        '''
        return self.compare_frames_goal_region (ith_frame, self.selected_region_of_interest_index)

    @staticmethod
    def image_processing_header ():
        return ["goal_background", "goal_previous_iteration"]

    @staticmethod
    def CASU_names ():
        return ['goal 1', 'goal 2'] + ['passive %d' % (index) for index in xrange (1, Corridor2Start2GoalArena.NUMBER_PASSIVE_CASUs + 1)]

    ROI_PICKER = None

    @staticmethod
    def roi_picker ():
        if Corridor2Start2GoalArena.ROI_PICKER == None:
            Corridor2Start2GoalArena.ROI_PICKER = roi_picker.Corridor2Start2GoalROIPicker (None)
        return Corridor2Start2GoalArena.ROI_PICKER

    def write_properties (self):
        """
        Save the arena properties for later reference.
        """
        AbstractVideoTapeableArena.write_properties (self, Corridor2Start2GoalArena.CASU_names ())

STRING_2_CLASS = {
    'CircularArena' : CircularArena,
    'TwoCircularArenas' : TwoCircularArenas,
    'Corridor2Start2GoalArena' : Corridor2Start2GoalArena,
    }
