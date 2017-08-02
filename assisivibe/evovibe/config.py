#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os.path

import assisivibe.common.arena as arena
import assisivibe.common.best_config as best_config
from assisivibe.common.best_config import Parameter
from assisivibe.common.best_config import ParameterIntBounded
from assisivibe.common.best_config import ParameterSetValues
import assisivibe.common.image_processing_functions as image_processing_functions
import assisivibe.common.segments as segments

import chromosome

class Config (best_config.Config):
    """
    Configuration setup of a run of the ASSISI PatVibe system.
    """

    def __init__ (self, filename = 'config2'):
        best_config.Config.__init__ (self, [
            ParameterIntBounded (
                'number_bees',
                'Number of bees',
                min_value = 1,
                max_value = None),
            ParameterIntBounded (
                'number_generations',
                'Number of generations of the evolutionary algorithm',
                min_value = 10,
                max_value = None),
            ParameterIntBounded (
                'population_size',
                'Population size of the evolutionary algorithm',
                min_value = 1,
                max_value = None),
            ParameterSetValues (
                'arena_type',
                'Arena to use',
                [(k, k) for k in arena.STRING_2_CLASS.keys ()]),
            ParameterSetValues (
                'chromosome_type',
                'Chromosome to use',
                [(k, k) for k in chromosome.CHROMOSOME_METHODS.keys ()],
                path_in_dictionary = ['chromosome']),
            ParameterIntBounded (
                'number_fitness_evaluations_per_chromosome',
                'How many fitness evaluation repetitions to perform (per chromosome)',
                min_value = 1,
                max_value = None,
                path_in_dictionary = ['fitness_function']),
            Parameter (
                'evaluation_proceeding',
                'How to evaluate chromosomes',
                parse_data = eval,
                path_in_dictionary = ['fitness_function']),
            Parameter (
                'has_blip',
                'Turn the LED between action sequence segments',
                parse_data = bool,
                default_value = True,
                path_in_dictionary = ['fitness_function']),
            ParameterIntBounded (
                'interval_current_previous_frame',
                'Time interval (in seconds) between compared frames',
                min_value = 1,
                max_value = None,
                path_in_dictionary = ['fitness_function', 'image_processing']),
            ParameterIntBounded (
                'pixel_count_previous_frame_threshold',
                'Threshold to use when comparing current frame with a previous frame',
                min_value = 0,
                max_value = None,
                path_in_dictionary = ['fitness_function', 'image_processing']),
            ParameterIntBounded (
                'pixel_count_background_threshold',
                'Threshold to use when comparing current frame image with background image',
                min_value = 0,
                max_value = None,
                path_in_dictionary = ['fitness_function', 'image_processing']),
            ParameterIntBounded (
                'same_colour_threshold',
                'Threshold to use when computing difference in pixel colour',
                min_value = 0,
                max_value = 100,
                default_value = 25,
                path_in_dictionary = ['fitness_function', 'image_processing']),
            ParameterSetValues (
                'image_processing_function',
                'Function used to process frames',
                [(ipf.code, ipf.description) for ipf in image_processing_functions.FUNCTIONs],
                path_in_dictionary = ['fitness_function', 'image_processing']),
            ParameterIntBounded (
                'bee_readiness_video_length',
                'Length of the video (in seconds) that is recorded to see if bees are ready',
                min_value = 10,
                max_value = None,
                path_in_dictionary = ['fitness_function', 'bee_ready']),
            ParameterIntBounded (
                'bee_readiness_minimum_percentage_bees',
                'Minimum percentage of bees that should be in a region of interest so that chromosome evaluation can start',
                min_value = 10,
                max_value = None,
                path_in_dictionary = ['fitness_function', 'bee_ready']),
            ParameterIntBounded (
                'number_fitness_evaluations_per_episode',
                'How many evaluations to perform with a set of bees',
                min_value = 1,
                max_value = 60,
                path_in_dictionary = ['episode']),
            ParameterIntBounded (
                'bee_familiarisation_time',
                'How many seconds to wait before testing the first vibration pattern in a set of bees',
                min_value = 0,
                max_value = 300,
                default_value = 0,
                path_in_dictionary = ['episode']),
            ParameterIntBounded (
                'image_width',
                'Image width in pixels',
                min_value = 100,
                max_value = None,
                default_value = 600,
                path_in_dictionary = ['video']),
            ParameterIntBounded (
                'image_height',
                'Image height in pixels',
                min_value = 100,
                max_value = None,
                default_value = 600,
                path_in_dictionary = ['video']),
            ParameterIntBounded (
                'crop_top',
                'Pixels to crop at top',
                min_value = 0,
                max_value = None,
                path_in_dictionary = ['video']),
            ParameterIntBounded (
                'crop_left',
                'Pixels to crop at left',
                min_value = 0,
                max_value = None,
                path_in_dictionary = ['video']),
            ParameterIntBounded (
                'frames_per_second',
                'Frames per second',
                min_value = 0,
                max_value = None,
                path_in_dictionary = ['video']),
            ParameterIntBounded (
                'bee_area_pixels',
                'Number of pixels occupied by a bee',
                min_value = 1,
                max_value = None,
                path_in_dictionary = ['video']),
            ParameterIntBounded (
                'camera_autofocus_time',
                'How much time to wait before starting the background video.',
                min_value = 0,
                max_value = None,
                path_in_dictionary = ['video']),
            ])
        if os.path.isfile (filename):
            self.load_from_yaml_file (filename)
        else:
            self.ask_user ()
        self.crop_right = arena.CAMERA_RESOLUTION_X - self.image_width - self.crop_left
        self.crop_bottom = arena.CAMERA_RESOLUTION_Y - self.image_height - self.crop_top

    def status (self):
        """
        Do a diagnosis of this experimental configuration.
        """
        print ("\n\n* Configuration Setup *")
        print ("----------------------------------------------------------------")
        print (self, end='')
        print ("----------------------------------------------------------------")
        raw_input ('  Press ENTER to continue. ')

if __name__ == '__main__':
    print (Config ('config'))
