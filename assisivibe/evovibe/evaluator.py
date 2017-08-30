#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import time
import subprocess #spawn new processes
import csv
import numpy
import os
import random
import sys

import numpy as np


from scipy.ndimage import gaussian_filter
from skimage import io
from skimage.color.colorconv import rgb2grey
from skimage.feature.blob import blob_dog
from skimage.morphology import reconstruction, erosion, dilation
from skimage.morphology.grey import opening
from skimage.morphology.selem import diamond
from skimage.util.dtype import img_as_float
from skimage.feature import blob_doh
from skimage.morphology import square

import assisipy

import assisivibe.common.image_processing_functions as image_processing_functions
import assisivibe.common.segments as segments
import assisivibe.common.util as util

import chromosome

# Column indexes in file population2.csv
POP_GENERATION       = 0
POP_CHROMOSOME_GENES = 1

# Column indexes in file evaluation2.csv
EVA_GENERATION       = 0
EVA_EPISODE          = 1
EVA_ITERATION        = 2
EVA_SELECTED_ARENA   = 3
EVA_ACTIVE_ROI       = 4
EVA_TIMESTAMP        = 5
EVA_VALUE            = 6
EVA_CHROMOSOME_GENES = 7

# Column indexes in file partial2.csv
PRT_GENERATION       = 0
PRT_EPISODE          = 1
PRT_FITNESS          = 2
PRT_CHROMOSOME_GENES = 3


class Evaluator:
    """
    Class that implements the evaluator used by the inspyred evolutionary algorithm classes.
    The evaluator computes the fitness value of each chromosome.  Each chromosome represents a vibration model.

    This evaluator is used by inspyred to compute the fitness value of the initial value.
    The evolve method enters a loop whose end condition depends on the terminator used.
    Inside the loop, it selects the next population, evalutes the chromosomes in the population,
    replace chromosomes in the population, archive chromosomes, increment
    the generation number counter, call the observers.

    :param config: A Python object with the following attributes
    """
    def __init__ (self, config, episode, experiment_folder, generation_number = 0):
        self.config = config
        self.episode = episode
        self.experiment_folder = experiment_folder
        self.generation_number = generation_number
        self.segments = segments.Segments (config.evaluation_proceeding)
        self.segments.compute_first_last_frames (config.frames_per_second, config.has_blip)
        self.number_analysed_frames = self.segments.total_number_frames ()
        # initialise the evaluation values reduce function
        self.EVALUATION_VALUES_REDUCE_FUNCTION = {
            'average'                             : self.evr_average ,
            'average_without_best_worst'          : self.evr_average_without_best_worst ,
            'weighted_average'                    : self.evr_range_value_weighted_average ,
            'range_value_weighted_average'        : self.evr_range_value_weighted_average ,
            'standard_deviation_weighted_average' : self.evr_standard_deviation_weighted_average }
        self._evaluation_values_reduce = self.EVALUATION_VALUES_REDUCE_FUNCTION ['average']
        # initialise the evaluation image processing function
        self.image_processing_function = image_processing_functions.STRING_2_OBJECT [config.image_processing_function].function

    def population_evaluator (self, candidates, args = None):
        """
        Evaluate a population.  This is the main method of this class and the one that is used by the evaluator function of the ES class of inspyred package.
        Chromosomes are evaluated in random order, even each fitness evaluation repetition.
        """
        self.save_population (candidates)
        evaluation_sequence = []
        for (index, chromosome) in enumerate (candidates):
            evaluation_sequence.extend (self.config.number_fitness_evaluations_per_chromosome * [(index, chromosome)])
        random.shuffle (evaluation_sequence)
        fitness_evaluations = []
        for _ in xrange (len (candidates)):
            fitness_evaluations.append ([])
        for (index, chromosome) in evaluation_sequence:
            fitness_evaluations [index].append (self.iteration_step (chromosome, len (fitness_evaluations [index])))
        result = [self._evaluation_values_reduce (fe) for fe in fitness_evaluations]
        self.save_partial (candidates, result)
        print ('\n\n* End Of Generation *')
        print ("\n  Population fitness of generation %d is %s" % (self.generation_number, str (result)))
        self.generation_number += 1
        return result

    def save_population (self, candidates):
        '''
        Save the chromosome population. This is done before evaluating a population.
        '''
        fp = open (self.experiment_folder + "population2.csv", 'a')
        f = csv.writer (fp, delimiter = ',', quoting = csv.QUOTE_NONE, quotechar = '"')
        for chromosome in candidates:
            row = [self.generation_number] + chromosome
            f.writerow (row)
        fp.close ()

    def save_partial (self, candidates, fitnesses):
        '''
        Save the chromosome fitness information. This is done after evaluating a population.
        '''
        fp = open (self.experiment_folder + "partial2.csv", 'a')
        f = csv.writer (fp, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar = '"')
        for result, chromosome in zip (fitnesses, candidates):
            row = [
                self.generation_number,
                self.episode.episode_index,
                result
            ] + chromosome
            f.writerow (row)
        fp.close ()

    def evr_average (self, values):
        """Reduce evaluation values by computing the average"""
        return sum (values) / self.config.number_fitness_evaluations_per_chromosome

    def evr_average_without_best_worst (self, values):
        """
        Reduce evaluation values by taking the best and worst and then computing the average"""
        return (sum (values) - max (values) - min (values)) / (self.config.number_fitness_evaluations_per_chromosome - 2)

    def evr_range_value_weighted_average (self, values):
        best = max (values)
        worst = min (values)
        mean = sum (values) / self.config.number_fitness_evaluations_per_chromosome
        weight = 1.0 * (self.image_processing_function.range_length - (best - worst)) / self.image_processing_function.range_length
        return mean * weight

    def evr_standard_deviation_weighted_average (self, values):
        mean = sum (values) / self.config.number_fitness_evaluations_per_chromosome
        weight = 1.0 * (self.image_processing_function.range_length - 2 * numpy.std (values)) / self.image_processing_function.range_length
        return mean * weight
        
    def iteration_step (self, candidate, index_evaluation):
        """
        Experimental step where a candidate chromosome evaluation is done.
        """
        c2s = chromosome.STRING_2_CLASS [self.config.chromosome_type].to_string (candidate)
        self.episode.increment_evaluation_counter ()
        print ("\n\n* Fitness Evaluation *\n  Episode %d - Evaluation %d" % (self.episode.episode_index, self.episode.current_evaluation_in_episode))

        index = 1
        print ('Checking if bees are dispersed...')
        while self.segment () < self.config.dispersion_threshold:
            print ('At attempt #%d bees are not dispersed' % (index))
            index += 1
        
        picked_arena = self.episode.select_arena ()
        (recording_process, filename_real) = self.start_iteration_video ()
        print ("     Starting vibration model: %s" % (c2s))
        time_start_vibration_pattern = picked_arena.run_vibration_model (self.config, candidate)
        print ("     Vibration model finished!")
        recording_process.wait ()
        print ("     Iteration video finished!")
        self.split_iteration_video (filename_real)
        self.compare_images (picked_arena)
        evaluation_score = self.compute_evaluation (picked_arena)
        self.write_evaluation (picked_arena, candidate, evaluation_score, time_start_vibration_pattern)
        print ("\n  Evaluation of %s is %.1f" % (c2s, evaluation_score))
        return evaluation_score
                    
    def start_iteration_video (self):
        """
        Starts the iteration video.  This video will record a chromosome evaluation and the bee spreading period.

        :return: a tuple with the process that records the iteration the video filename
        """
        print ("\n* ** Starting Iteration Video...")
        filename_real = self.episode.current_path + 'iterationVideo_' + str (self.episode.current_evaluation_in_episode) + '.avi'
        p = util.record_video (filename_real, self.number_analysed_frames, self.config.frames_per_second, self.config.crop_left, self.config.crop_right, self.config.crop_top, self.config.crop_bottom)
        return (p, filename_real)


    def split_iteration_video (self, filename_real):
        """
        Split the iteration video into images.  We only need the images from the evaluation run time period.

        The images are written in folder tmp relative to 
        """
        print ("\n* ** Starting Video Split...")
        # bashCommandSplit = "avconv" + \
        #                    " -i " + filename_real + \
        #                    " -r " + str (self.config.frames_per_second) + \
        #                    " -loglevel error" + \
        #                    " -frames:v " + str (self.number_analysed_frames) + \
        #                    " -f image2 tmp/iteration-image-%4d.jpg"
        bashCommandSplit = "ffmpeg" + \
                           " -i " + filename_real + \
                           " -r " + str (self.config.frames_per_second) + \
                           " -loglevel error" + \
                           " -frames " + str (self.number_analysed_frames) + \
                           " -f image2 tmp/iteration-frame-%4d.jpg"
        p = subprocess.Popen (bashCommandSplit, shell=True, executable='/bin/bash') #to create and save the real images from the video depending on the iteration number
        p.wait ()
        print ("     Finished spliting iteration " + str (self.episode.current_evaluation_in_episode) + " video.")

    def compare_images (self, picked_arena):
        """
        Compare images created in a chromosome evaluation and generate a CSV file.
        The first column has the pixel difference between the current iteration image and the background image in the first CASU.
        The second column has the pixel difference between the current iteration image and the previous iteration image in the first CASU.
        The third column has the pixel difference between the current iteration image and the background image in the second CASU.
        The fourth column has the pixel difference between the current iteration image and the previous iteration image in the second CASU.
        """
        print ("\n* ** Comparing Images...")
        fp = open (self.episode.current_path + "image-processing_" + str (self.episode.current_evaluation_in_episode) + ".csv", 'w')
        f = csv.writer (fp, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar = '"')
        f.writerow (picked_arena.image_processing_header ())
        for i in xrange (1, self.number_analysed_frames + 1):
            f.writerow (picked_arena.compare_frames (i))
        fp.close ()
        print ("     Finished comparing images from iteration " + str (self.episode.current_evaluation_in_episode) + " video.")

    def compute_evaluation (self, picked_arena):
        '''
        Compute the evaluation of the current chromosome.
        The fitness value depends on the image processing function. This function is applied to each processed frame.
        
        See method compare_images(self,arena) for information about how frames are processed.
        '''
        result = 0
        index_segment = 0
        asegment = self.segments [index_segment]
        with open (self.episode.current_path + "image-processing_" + str (self.episode.current_evaluation_in_episode) + ".csv", 'r') as fp:
            freader = csv.reader (fp, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar = '"')
            freader.next () # skip header row
            for index_frame in xrange (1, self.number_analysed_frames + 1):
                row = freader.next ()
                if asegment.last_frame < index_frame:
                    index_segment += 1
                    if index_segment < len (self.segments):
                        asegment = self.segments [index_segment]
                    else:
                        break
                if asegment.first_frame <= index_frame <= asegment.last_frame and asegment.type == segments.SGT_VIBRATION:
                    result += self.image_processing_function (self.config, picked_arena.selected_region_of_interest_index, row)
        return result

    def write_evaluation (self, picked_arena, candidate, evaluation_score, time_start_vibration_pattern):
        """
        Save the result of a chromosome evaluation.
        """
        with open (self.experiment_folder + "evaluation2.csv", 'a') as fp:
            f = csv.writer (fp, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar = '"')
            f.writerow ([
                self.generation_number,
                self.episode.episode_index,
                self.episode.current_evaluation_in_episode,
                picked_arena.index,
                picked_arena.list_workers_stubs [picked_arena.selected_region_of_interest_index].casu_number,
                time_start_vibration_pattern,
                evaluation_score] + candidate)
            fp.close ()


    def segment(self, noise_threshold_upper=0.6, noise_threshold_lower=0.2):

        filename = self.episode.current_path + "segment.avi"
        p = util.record_video (filename, self.config.fatigue_video_number_frames, self.config.fatigue_video_frames_per_second, self.config.crop_left, self.config.crop_right, self.config.crop_top, self.config.crop_bottom)
        p.wait ()
        p = util.split_video (filename, self.config.fatigue_video_number_frames, self.config.fatigue_video_frames_per_second, 'tmp/segment_%4d.png')
        p.wait ()

        background_folder = self.episode.current_path + 'Background.jpg'
        prev = None
        first_run = False

        movement = []

        background = img_as_float(rgb2grey(io.imread(background_folder)))

        for ith_frame in xrange (1, self.config.fatigue_video_number_frames + 1):
            frame = 'tmp/segment_%04d.png' % (ith_frame)

            # Convert to float: Important for subtraction later which won't work with uint8
            foreground = img_as_float(rgb2grey(io.imread(frame)))
            image = np.abs(foreground - background)

            #image = gaussian_filter(image, 1)

            seed = np.copy(image)
            seed[1:-1, 1:-1] = image.min()
            mask = image

            dilated = reconstruction(seed, mask, method='dilation')

            clean = image - dilated
            clean[clean < noise_threshold_lower] = 0.0
            clean[clean > noise_threshold_upper] = 0.0
            clean = opening(clean, square (3))

            # Blob detection
            blobs_doh = blob_dog(clean*255, min_sigma=10, max_sigma=30, threshold=0.1, overlap=0.99)
            blobs_doh /= np.ones (shape = (self.config.image_width, self.config.image_height))

            std = np.std(blobs_doh, axis=0)
            dispersion = std[0]*std[1]

            if first_run:
                fig, (ax0, ax1, ax2) = plt.subplots(nrows=1,
                                                    ncols=3,
                                                    figsize=(15, 8),
                                                    sharex=True,
                                                    sharey=True)

                ax0.imshow(image, cmap='gray')
                ax0.set_title('difference image')
                ax0.axis('off')
                ax0.set_adjustable('box-forced')

                ax1.imshow(clean, vmin=image.min(), vmax=image.max(), cmap='gray')
                ax1.set_title('cleaned')
                ax1.axis('off')
                ax1.set_adjustable('box-forced')

                ax2.imshow(foreground, cmap='gray')
                print('Min: %f, Max: %f' %(np.min(clean), np.max(clean)))
                ax2.set_title('blob')
                ax2.axis('off')
                ax2.set_adjustable('box-forced')
                print(blobs_doh)
                for blob in blobs_doh:
                    y, x, r = blob
                    c = plt.Circle((x, y), r, color='c', linewidth=2, fill=False)
                    ax2.add_patch(c)

                fig.tight_layout()
                plt.show()

                first_run = False

        print ('dispersion is ', dispersion)
        return dispersion
