"""
Extends inspyred with the functionality to continue an evoluationary algorithm that was stopped due to some reason.
"""

import collections
import copy

class ContinueEvaluator:
    EVALUATE_INITIAL_POPULATION = 0
    EVALUATE_FIRST_OFFSPRING = 1
    NORMAL_EVALUATION = 2
    def __init__ (self, normal_evaluator, parents_fitness, offspring_fitness):
        self._normal_evaluator = normal_evaluator
        self._parents_fitness = copy.copy (parents_fitness)
        self._offspring_fitness = copy.copy (offspring_fitness)
        self._state = ContinueEvaluator.EVALUATE_INITIAL_POPULATION
        # print "contructor ContinueEvaluator", self._parents_fitness
        # print "contructor ContinueEvaluator", self._offspring_fitness
        # self.nb = 1
        
    def evaluator (self, candidates, args):
        # print "ContinueEvaluator evaluator call #", self.nb, " with candidates", candidates
        # self.nb += 1
        if self._state == ContinueEvaluator.EVALUATE_INITIAL_POPULATION:
            assert len (candidates) >= len (self._parents_fitness), "Candidates are %s with %d elements" % (candidates, len (candidates))
            if len (self._offspring_fitness) > 0 or len (candidates) == len (self._parents_fitness):
                self._state = ContinueEvaluator.EVALUATE_FIRST_OFFSPRING
                return self._parents_fitness
            else:
                self._state = ContinueEvaluator.NORMAL_EVALUATION
                candidates_missing_fitness = candidates [len (self._parents_fitness):]
                print "candidates from parent missing fitness:", candidates_missing_fitness, "of", candidates
                fitness_rest_candidates = self._normal_evaluator (candidates_missing_fitness, args)
                return self._parents_fitness + fitness_rest_candidates
        elif self._state == ContinueEvaluator.EVALUATE_FIRST_OFFSPRING:
            assert len (candidates) >= len (self._offspring_fitness)
            self._state = ContinueEvaluator.NORMAL_EVALUATION
            candidates_missing_fitness = candidates [len (self._offspring_fitness):]
            print "candidates from offspring missing fitness:", candidates_missing_fitness, "of", candidates
            fitness_rest_candidates = self._normal_evaluator (candidates_missing_fitness, args)
            return self._offspring_fitness + fitness_rest_candidates
        elif self._state == ContinueEvaluator.NORMAL_EVALUATION:
            return self._normal_evaluator (candidates, args)
        else:
            assert False, "Invalid state of ContinueEvaluator instance"

class ContinueVariator:
    VARIATE_FIRST_POPULATION = 0
    NORMAL_VARIATION = 1

    def __init__ (self, offsprings):
        self._state = ContinueVariator.VARIATE_FIRST_POPULATION
        self._offsprings = copy.deepcopy (offsprings)
        # print "constructor ContinueVariator", self._offsprings
        # self.nb = 1

    def variator (self, random, candidates, args):
        # print "ContinueVariator variator call #", self.nb, " with candidates", candidates
        # self.nb += 1
        if self._state == ContinueVariator.VARIATE_FIRST_POPULATION:
            self._state = ContinueVariator.NORMAL_VARIATION
            return self._offsprings
        elif self._state == ContinueVariator.NORMAL_VARIATION:
            return candidates
        else:
            assert False, "Invalid state of ContinueVariator instance"

class ContinueObserver:
    def __init__ (self, normal_observer, delta_generation, number_observers):
        self.normal_observer = normal_observer
        self.delta_generation = delta_generation
        self.state = number_observers

    def observer (self, population, num_generations, num_evaluations, args):
        if self.state > 0:
            self.state -= 1
        else:
            self.normal_observer (population, num_generations + self.delta_generation, num_evaluations, args)

def continue_evolution (evolutionary_computation, population_parents, population_offsprings, parents_fitness, offspring_fitness,
                        generator, evaluator, number_generations, maximize=True, bounder=None, **args):
    '''
    Parameter number_generations Number of generations that have been processed by the observers.
    '''

    #(len (population_parents) != len (parents_fitness) or (len (population_parents) == len (population_offsprings) >= len (offspring_fitness))) and \
        # "if for every parent there is a fitness then " + \
        # "the number of parents should be equal to the number offspring and " + \
        # "there should be at least as many offsprings as offspring's fitness" \
        # if not ((len (population_parents) != len (parents_fitness) or (len (population_parents) == len (population_offsprings) >= len (offspring_fitness)))) else \
    
    assert len (population_parents) >= len (population_offsprings) and \
        len (population_parents) >= len (parents_fitness) and \
        (len (population_parents) == len (parents_fitness) or (len (population_offsprings) == 0 and len (offspring_fitness) == 0)), \
        "the number of parents should be greater than or equal to the number of offspring\t#pp=" + str (len (population_parents)) + "\t#po=" + str (len (population_offsprings))  \
        if not (len (population_parents) >= len (population_offsprings)) else \
        "there should be at least as many parents as there are parents' fitness" \
        if not (len (population_parents) >= len (parents_fitness)) else \
        "if there are not enough parents' fitness then " + \
        "the number of offsprings should be zero and " + \
        "the number of offsprings' fitness should be zero\t#pp=" + str (len (population_parents)) + "\t#po=" + str (len (population_offsprings))+ "\t#pf=" + str (len (parents_fitness)) + "\t#of=" + str (len (offspring_fitness))
    
    
    if 'pop_size' in args:
        raise Exception ("continue evolution does not use parameter pop_size")
    if 'seeds' in args:
        raise Exception ("continue evolution does not use parameter seeds")
    if len (population_parents) < len (population_offsprings):
        raise Exception ("there are more offsprings than parents")
    if len (population_parents) < len (parents_fitness):
        raise Exception ("size of population of parents does not match number of parents fitness")
    ce = ContinueEvaluator (evaluator, parents_fitness, offspring_fitness)
    if isinstance (population_offsprings, collections.Iterable) and len (population_offsprings) > 0:
        cv = ContinueVariator (population_offsprings)
        if isinstance (evolutionary_computation.variator, collections.Iterable):
            nv = [v for v in evolutionary_computation.variator] + [cv.variator]
        else:
            nv = [evolutionary_computation.variator] + [cv.variator]
        evolutionary_computation.variator = nv
    if isinstance (evolutionary_computation.observer, collections.Iterable):
        N = len (evolutionary_computation.observer) if len (offspring_fitness) > 0 \
		 or (len (offspring_fitness) == 0 and len (parents_fitness) == len (population_parents)) \
		else 0
        nlo = [ContinueObserver (o, number_generations, N).observer for o in evolutionary_computation.observer]
    else:
        N = 1 if len (offspring_fitness) > 0 \
	    or (len (offspring_fitness) == 0 and len (parents_fitness) == len (population_parents)) \
            else 0
        nlo = [ContinueObserver (evolutionary_computation.observer, number_generations, N).observer]
    evolutionary_computation.observer = nlo
    return evolutionary_computation.evolve (
        generator,
        ce.evaluator,
        len (population_parents),
        population_parents,
        maximize,
        bounder,
        **args)
    
if __name__ == '__main__':
    pass
