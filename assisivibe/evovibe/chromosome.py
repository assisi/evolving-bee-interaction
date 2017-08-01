#!/usr/bin/env python
# -*- coding: utf-8 -*-

# chromosomes used in the incremental evolution work.
# Pedro Mariano
# Ziad Salem
# Payam Zahadat

import assisipy.casu

import random
import time
import copy
import math

# vibration frequency domain
MIN_FREQUENCY = 300
MAX_FREQUENCY = 1500  # assisipy.casu.VIBE_FREQ_MAX
STEP_FREQUENCY = 10
STDDEV_FREQUENCY = (MAX_FREQUENCY - MIN_FREQUENCY) / 10.0
# only for geometric perturbation # SUCCESS_FREQUENCY = 1.0 / (((MAX_FREQUENCY - MIN_FREQUENCY) // STEP_FREQUENCY + 1) / 10 + 1.0)

# vibration period domain, pause period domain
MIN_PERIOD = 100  # assisipy.casu.VIBE_PERIOD_MIN
MAX_PERIOD = 1000
STEP_PERIOD = 10
STDDEV_PERIOD = 300 # (MAX_PERIOD - MIN_PERIOD) / 10.0
# only for geometric perturbation # SUCCESS_PERIOD = 1.0 / (((MAX_PERIOD - MIN_PERIOD) // STEP_PERIOD + 1) / 10 + 1.0)

# vibration intensity domain
MIN_INTENSITY = 5
STEP_INTENSITY = 5
MAX_INTENSITY = 50 # assisipy.casu.VIBE_AMP_MAX
STDDEV_INTENSITY = 10

BITRATE = 16

def geometric_perturbation (prng, current_value, min_value, max_value, step_value, success):
    change = 0
    while prng.random () >= success:
        change += step_value
    if prng.random () < 0.5:
        change = -change
    return ((current_value + change - min_value) % (max_value - min_value)) + min_value

def gaussian_perturbation (prng, current_value, min_value, max_value, step_value, stddev):
    change = prng.gauss (0, stddev)
    new_value = int (round (current_value + change))
    remainder = (new_value - min_value) % step_value
    new_value += -remainder + (step_value if 2 * remainder >= step_value > 1 else 0)
    new_value = (new_value - min_value) % (max_value - min_value + step_value) + min_value
    return new_value



class SinglePulse1sGenesFrequencyPause:
    """
    This chromosome contains two genes that represent the pulse frequency, and pause time.  The pulse period is always 1s.
    """
    VIBRATION_AMPLITUDE = 50
    PULSE_PERIOD = 1000

    @staticmethod
    def run_vibration_model (chromosome, the_casu):
        """
        Run the vibration model represented by the given SinglePulseGenesPulse chromosome.
        """
        frequency        = chromosome [0]
        pause_period     = chromosome [1]
        vibration_period = SinglePulse1sGenesFrequencyPause.PULSE_PERIOD - chromosome [1]
        amplitude        = SinglePulse1sGenesFrequencyPause.VIBRATION_AMPLITUDE
        print ('       Playing SinglePulse1sGenesFrequencyPause %dHz %dms' % (frequency, pause_period))
        vibe_periods = [vibration_period,  pause_period]
        vibe_freqs   = [       frequency,             1]
        vibe_amps    = [       amplitude,             0]
        the_casu.set_vibration_pattern (vibe_periods, vibe_freqs, vibe_amps)

    @staticmethod
    def random_generator (random, args = None):
        """
        Return a random instance of a simple SinglePulseGenesPulse chromosome.
        This method is used as a generator by the evolutionary algorithm.
        """
        frequency    = random.randrange (MIN_FREQUENCY, MAX_FREQUENCY + 1,  STEP_FREQUENCY)
        pause_period = random.randrange (MIN_PERIOD,    SinglePulse1sGenesFrequencyPause.max_period () + 1,     STEP_PERIOD)
        return [frequency, pause_period]

    @staticmethod
    def get_variator ():
        import inspyred
        @inspyred.ec.variators.mutator
        def variator (random, candidate, args = None):
            result = copy.copy (candidate)
            gene_index = random.randrange (2)
            if gene_index == 0:
                new_gene = gaussian_perturbation (random, candidate [0], MIN_FREQUENCY, MAX_FREQUENCY, STEP_FREQUENCY, STDDEV_FREQUENCY)
                result [0] = new_gene
            elif gene_index == 1:
                new_gene = gaussian_perturbation (random, candidate [1], MIN_PERIOD, SinglePulse1sGenesFrequencyPause.max_period (), STEP_PERIOD, STDDEV_PERIOD)
                result [1] = new_gene
            return result
        return variator

    @staticmethod
    def get_genes ():
        return [Gene (name = 'vibration frequency',    unit = 'Hz', min_value = MIN_FREQUENCY, max_value = MAX_FREQUENCY, step = STEP_FREQUENCY, stddev = STDDEV_FREQUENCY),
                Gene (name = 'pause period', unit = 'ms', min_value = MIN_PERIOD,    max_value = SinglePulse1sGenesPulse.max_period (), step = STEP_PERIOD, stddev = STDDEV_PERIOD)]

    @staticmethod
    def max_period ():
        return max (MIN_PERIOD, min (SinglePulse1sGenesFrequencyPause.PULSE_PERIOD - MIN_PERIOD, MAX_PERIOD))

class SinglePulse1sGenesPulse (AbstractChromosome):
    """
    This chromosome contains the gene that control a vibration pulse with 1
    second of duration.  The genes are the frequency, pause period and
    amplitude.
    """
    PULSE_PERIOD = 1000

    @staticmethod
    def run_vibration_model (chromosome, the_casu):
        """
        Run the vibration model represented by the given SinglePulse1sGenesPulse chromosome.
        """
        frequency        = chromosome [0]
        pause_period     = chromosome [1]
        vibration_period = SinglePulse1sGenesPulse.PULSE_PERIOD - chromosome [1]
        amplitude        = chromosome [2]
        print ('       Playing SinglePulse1sGenesPulse %dHz V%dms P%dms' % (frequency, vibration_period, pause_period))
        vibe_periods = [vibration_period,  pause_period]
        vibe_freqs   = [       frequency,             1]
        vibe_amps    = [       amplitude,             0]
        the_casu.set_vibration_pattern (vibe_periods, vibe_freqs, vibe_amps)

    @staticmethod
    def random_generator (random, args = None):
        """
        Return a random instance of a simple SinglePulse1sGenesPulse chromosome.
        This method is used as a generator by the evolutionary algorithm.
        """
        frequency    = random.randrange (MIN_FREQUENCY , MAX_FREQUENCY + 1                         , STEP_FREQUENCY)
        pause_period = random.randrange (MIN_PERIOD    , SinglePulse1sGenesPulse.max_period () + 1 , STEP_PERIOD)
        amplitude    = random.randrange (MIN_INTENSITY , MAX_INTENSITY                             , STEP_INTENSITY)
        return [frequency, pause_period, amplitude]

    @staticmethod
    def get_variator ():
        import inspyred
        @inspyred.ec.variators.mutator
        def variator (random, candidate, args = None):
            result = copy.copy (candidate)
            gene_index = random.randrange (3)
            if gene_index == 0:
                new_gene = gaussian_perturbation (random, candidate [0], MIN_FREQUENCY, MAX_FREQUENCY, STEP_FREQUENCY, STDDEV_FREQUENCY)
                result [0] = new_gene
            elif gene_index == 1:
                new_gene = gaussian_perturbation (random, candidate [1], MIN_PERIOD, SinglePulse1sGenesPulse.max_period (), STEP_PERIOD, STDDEV_PERIOD)
                result [1] = new_gene
            elif gene_index == 2:
                new_gene = gaussian_perturbation (random, candidate [2], MIN_INTENSITY, MAX_INTENSITY, STEP_INTENSITY, STDDEV_INTENSITY)
                result [2] = new_gene
            return result
        return variator

    @staticmethod
    def get_genes ():
        return [Gene (name = 'vibration frequency',    unit = 'Hz', min_value = MIN_FREQUENCY, max_value = MAX_FREQUENCY, step = STEP_FREQUENCY, stddev = STDDEV_FREQUENCY),
                Gene (name = 'pause period', unit = 'ms', min_value = MIN_PERIOD,    max_value = SinglePulse1sGenesPulse.max_period (), step = STEP_PERIOD, stddev = STDDEV_PERIOD),
                Gene (name = 'amplitude',    unit = '%',  min_value = MIN_INTENSITY, max_value = MAX_INTENSITY, step = STEP_INTENSITY, stddev = STDDEV_INTENSITY)]

    @staticmethod
    def max_period ():
        return max (MIN_PERIOD, min (SinglePulse1sGenesPulse.PULSE_PERIOD - MIN_PERIOD, MAX_PERIOD))

class Method:
    def __init__ (self, class_name):
        self.run_vibration_model = class_name.run_vibration_model
        self.variator = class_name.get_variator
        self.generator = class_name.random_generator
        self.get_genes = class_name.get_genes

    def __str__ (self):
        return 'run: ' + str (self.run_vibration_model) + ' variator: ' + str (self.variator) + ' generator: ' + str (self.generator)

CHROMOSOME_METHODS = {
    'SinglePulse1sGenesFrequencyPause' : Method (SinglePulse1sGenesFrequencyPause) ,
    'SinglePulse1sGenesPulse' : Method (SinglePulse1sGenesPulse) ,
    }

class Gene:
    '''
    Describes a gene in a chromosome.
    '''
    def __init__ (self, name, unit, min_value, max_value, step, stddev):
        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.stddev = stddev

    def __repr__ (self):
        return "'%s' %s %d %d %d %d" % (self.name, self.unit, self.min_value, self.max_value, self.step, self.stddev)

if __name__ == '__main__':
    pass
