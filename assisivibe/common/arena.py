#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import PIL.Image
import PIL.ImageChops
import subprocess
import time

import image_processing_functions
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

class AbstractVideoTapeableArena (BasicArena):
    """
    An arena that can be video taped, that has regions of interest, and that has controllable CASUs.

    The file names of the video frames are tmp/iteration-frame-NNNN.jpg.
    """
    def __init__ (self, dict_workers_stubs, casu_names, number_active_CASUs, number_ROIs, episode_path, img_path, index, config):
        BasicArena.__init__ (self, dict_workers_stubs, casu_names, number_active_CASUs)
        self.img_path = img_path
        self.index = index
        self.number_ROIs = number_ROIs
        self.same_colour_threshold_int = int (config.same_colour_threshold * 255 / 100)
        self.delta_frame = int (config.frames_per_second / config.interval_current_previous_frame)
        self.frame_template = 'tmp/iteration-frame-%04d.jpg'
        self.roi_template = '%sMask-%%d.jpg' % (self.img_path)
        self.background_filename = "%sBackground.jpg" % (episode_path)

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
        return image_processing_functions.compare_frames (
            ith_frame, self.delta_frame, self.number_ROIs, self.frame_template,
            self.roi_template, self.background_filename, self.same_colour_threshold_int)

    def write_properties (self, list_casu_names):
        '''
        Save the CASU numbers to file casu.properties.
        '''
        data = {}
        for a_worker_stub, a_casu_name in zip (self.list_workers_stubs, list_casu_names):
            data [a_casu_name] = a_worker_stub.casu_number
        with open (self.img_path + "casu.properties", 'w') as fp:
            yaml.dump (data, fp, default_flow_style = False)
            fp.close ()

class CircularArena (AbstractVideoTapeableArena):
    """
    A circular arena with a single casu.  Region of interest is circular
    """
    def __init__ (self, dict_workers_stubs, episode_path, img_path, index, config):
        """
        Ask the user the position of the arena, of the casu, and of the region of interest.
        """
        AbstractVideoTapeableArena.__init__ (self, dict_workers_stubs, CircularArena.ROI_names (), 1, CircularArena.number_ROIs (), episode_path, img_path, index, config)

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

STRING_2_CLASS = {
    'CircularArena' : CircularArena,
    'TwoCircularArenas' : TwoCircularArenas,
    }
