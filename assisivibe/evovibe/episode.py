#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import worker

import assisivibe.common.arena as arena
import assisivibe.common.util as util
import assisivibe.common.zmq_sock_utils as zmq_sock_utils

import subprocess
import os
import os.path
import PySide.QtGui
import random
import time

class Episode:
    """
    An episode represents a set of evaluations with a set of bees.

    This class is responsible for managing the initialisation and finish phase of episodes.  This class also manages the evaluation counter used in an episode.  The increment of this counter should be done at the beginning of an evaluation phase (see method evaluator.exp_step).

    In the initialisation phase the characteristics of the arena image have to be computed before bees are placed in the arena.  Then we ask the user to place the bees in the arena.  For documentation about the arena images, see module 'image'.

    In the finish phase we ask the user to remove the bees from the arena.

    This class can be used by the incremental evolution or by a parameter sweep.
    """

    def __init__ (self, config, worker_settings, experiment_folder, episode_index = 1):
        self.config = config
        self.worker_settings = worker_settings
        self.experiment_folder = experiment_folder
        self.current_evaluation_in_episode = 0
        self.episode_index = episode_index
        self.app = PySide.QtGui.QApplication ([])


    def initialise (self):
        """
        In the initialisation phase of an episode we:

        * create the background image;

        * ask the user for the characteristics of the arena(s) image and the CASUs;

        * ask the user to put bees in the arena(s);
        """
        self.current_path = "%sepisodes/%03d/" % (self.experiment_folder, self.episode_index)
        try:
            os.makedirs (self.current_path)
        except OSError:
            pass
        print ('\n\nPut new wax floor and arena(s).')
        print ('Turn off the lab light and close the lab door.')
        raw_input ('Press ENTER when ready ')
        print ('Waiting %d seconds for camera to adjust...' % (self.config.camera_autofocus_time))
        time.sleep (self.config.camera_autofocus_time)
        self.make_background_image ()
        self.ask_arenas ()
        if len (self.arenas) == 1:
            print ('\nPlace %d bees in the arena.' % self.config.number_bees)
        else:
            print ('\nPlace %d bees in each arena.' % self.config.number_bees)
        print ('Turn off the lab light and close the lab door.')
        raw_input ('Press ENTER when ready ')
        if self.config.bee_familiarisation_time > 0:
            print ("I'm going to wait %ds for the bees to relax." % (self.config.bee_familiarisation_time))
            time.sleep (self.config.bee_familiarisation_time)
            print ("Bees should be ready to go!\n")
        else:
            print ('Waiting %d seconds for camera to adjust...' % (self.config.camera_autofocus_time))
            time.sleep (self.config.camera_autofocus_time)

    def increment_evaluation_counter (self):
        """
        Increment the evaluation counter.  If we have reached the end of an episode, we finish it and start a new episode.
        """
        if (self.current_evaluation_in_episode == self.config.number_fitness_evaluations_per_episode):
            print ("\n\n* ** New Episode ** *")
            self.finish ()
            self.episode_index += 1
            self.initialise ()
            self.current_evaluation_in_episode = 1
        else:
            self.current_evaluation_in_episode += 1

    def make_background_image (self):
        """
        Create the background video and image.

        These are used by the bee
        aggregation functions to compute how bees are stopped.  The
        background video and images are created at start of an experiment
        and everytime we change bees.  Whenever we change bees, we may
        disturb the arena.  The bee aggregation is sensitive to changes between the background image and evaluation images.
        """
        print ("\n\n* ** Creating background image...")
        filename = self.current_path + 'Background.avi'
        p = util.record_video (filename, 1, 1, self.config.crop_left, self.config.crop_right, self.config.crop_top, self.config.crop_bottom, debug = True)
        p.wait ()
        bashCommandSplit = "ffmpeg" + \
            " -i " + filename + \
            " -r 0.1" + \
            " -loglevel error" + \
            " -f image2 " + self.current_path + "Background.jpg" #definition to extract the single image for background from the video
        p = subprocess.Popen (bashCommandSplit, shell = True, executable = '/bin/bash') #run the script of the extracting
        p.wait ()
        print ("background image is ready")

    def ask_arenas (self):
        """
        Ask the user how many arenas are going to be used and their characteristics.
        """
        go = True
        self.arenas = []
        index = 1
        for ws in self.worker_settings.values ():
            ws.in_use = False
        while go:
            img_path = "%sarena-%d/" % (self.current_path, index)
            arena_constructor = arena.STRING_2_CLASS [self.config.arena_type]
            new_arena = arena_constructor (self.worker_settings, self.current_path, img_path, index, self.config)
            roi_picker = arena_constructor.roi_picker ()
            roi_picker.set_background_image_path (self.current_path + "Background.jpg")
            roi_picker.showMaximized ()
            self.app.exec_ ()
            os.makedirs (img_path)
            roi_picker.create_mask_images (img_path)
            roi_picker.create_region_of_interests_image (img_path)
            roi_picker.write_properties (img_path)
            new_arena.write_properties ()
            self.arenas.append (new_arena)
            index += 1
            go = util.is_answer_yes ('Are there more arena(s)')

    def select_arena (self):
        """
        Check the status of the arenas and select an arena using a roulette wheel approach.
        Returns the selected arena.
        """
        ok = False
        while not ok:
            status = []
            total_sum = 0
            for an_arena in self.arenas:
                (value, temps) = an_arena.status ()
                total_sum += value
                status.append (value)
                print ("Temperature status: %s." % (str (temps)))
            if total_sum == 0:
                print ("All arenas have a temperature above the minimum threshold!")
                raw_input ("Press ENTER to try again. ")
            else:
                ok = True
        x = total_sum * random.random ()
        picked = 0
        print (x, "/", total_sum, status)
        while x >= status [picked]:
            x -= status [picked]
            picked += 1
        print ("Picked arena #%d." % (picked + 1))
        return self.arenas [picked]
        
    def finish (self, end_evolutionary_algorithm = False):
        """
        In the finish phase of an episode we:

        * tell the user to remove the bees from the arena;

        """
        print ("Remove the bees from the arena(s)!")
        if end_evolutionary_algorithm:
            print ('The program is going to finish!')
        raw_input ("When done, press ENTER to continue. ")

if __name__ == '__main__':
    import worker_settings
    lws = worker_settings.load_worker_settings ('workers')
    import config
    cfg = config.Config ()
    for ws in lws:
        print (ws)
        ws.connect_to_worker (cfg)
    dws = dict ([(ws.casu_number, ws) for ws in lws])
    epsd = Episode (cfg, dws, '/tmp/assisi/')
    epsd.initialise ()
    epsd.ask_user (None)
    epsd.increment_evaluation_counter ()
    picked_arena = epsd.select_arena ()
