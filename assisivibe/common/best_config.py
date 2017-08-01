# -*- coding: utf-8 -*-

import yaml
import copy

def identity (x):
    return x

def between (min_value, max_value, x):
    if min_value <= x <= max_value:
        return x
    else:
        raise ValueError ()

def compose (f, g, x):
    return f (g (x))

def list_element (the_list, x):
    sub = lambda x : x - 1
    f = lambda x : between (0, len (the_list) - 1, x)
    return compose (the_list.__getitem__, f, compose (sub, int, x))

def str2bool (x):
    return True if x == 'True' else False

class Parameter:
    '''
    Represents a parameter of a program.  Parameters can be set by the
    user, or read from a yaml file.

    Parameters in the yaml file are organized in tree like structure.  This
    serves to group related parameters.  Each parameter class provides a
    method that validates the value in the yaml file.

    The user can also set the parameters by entering in a text like
    interface.  Each parameter provides a method that provides an user
    prompt.  There is another method that parses the string that the user
    entered.  The result of parsing is fed to the validate method.
    '''
    def __init__ (self, name, description, path_in_dictionary = [], default_value = None, parse_data = identity):
        self.name = name
        self.description = description
        self.path_in_dictionary = path_in_dictionary
        self.default_value = default_value
        self.parse_data = parse_data
        self.has_value = False
        self.value = None

    def load_from_dictionary (self, dictionary):
        """
        Load a parameter value from the given dictionary.
        """
        pause = False
        try:
            for n in self.path_in_dictionary:
                dictionary = dictionary [n]
            self.value = dictionary [self.name]
        except KeyError as e:
            if self.default_value is None:
                raise e
            else:
                print "Using default value %s for %s!" % (self.default_value, self.name)
                self.value = self.default_value
                pause = True
        finally:
            self.has_value = True
        return pause

    def ask_user (self):
        while True:
            try:
                self.value = self.parse_string (raw_input (self.prompt ()))
                if self.validate_value (self.value):
                    self.has_value = True
                    return
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                if self.parse_string == eval:
                    print (e)
            print 'Invalid data!'

    def prompt (self):
        return self.description + '? '
    
    def parse_string (self, string):
        return self.parse_data (string)

    def validate_value (self, value):
        return True

class ParameterEnumeration (Parameter):
    def  __init__ (self, name, description, min_value, max_value, step_value, path_in_dictionary = [], default_value = None):
        Parameter.__init__ (self, name, description, path_in_dictionary, default_value, parse_data = int)
        self.min_value = min_value
        self.max_value = max_value
        self.step_value = step_value

    def prompt (self):
        result = self.descripton + ' {' + str (self.min_value)
        if self.min_value + self.step_value < self.max_value:
            result += ', ' + str (self.min_value + self.step_value)
        if self.min_value + 2 * self.step_value < self.max_value:
            result += ', ...'
        result += ', or ' + str (self.max_value) + '} ? '
        return result

    def parse_string (self, string):
        return int (string)

    def validate_value (self, value):
        return value in range (min_value, max_value + 1, step_value)

class ParameterIntBounded (Parameter):
    def  __init__ (self, name, description, min_value, max_value, path_in_dictionary = [], default_value = None):
        Parameter.__init__ (self, name, description, path_in_dictionary, default_value, parse_data = int)
        self.min_value = min_value
        self.max_value = max_value

    def prompt (self):
        result = self.description
        if self.min_value is None:
            result += ' ]-∞'
        else:
            result += ' [' + str (self.min_value)
        result += ', '
        if self.max_value is None:
            result += '+∞[ ? '
        else:
            result += str (self.max_value) + '] ? '
        return result

    def parse_string (self, string):
        return int (string)

    def validate_value (self, value):
        if self.min_value is not None and value >= self.min_value:
            return True
        elif self.max_value is not None and value <= self.max_value:
            return True
        else:
            return False

class ParameterSetValues (Parameter):
    def  __init__ (self, name, description, set_values, path_in_dictionary = [], default_value = None):
        Parameter.__init__ (self, name, description, path_in_dictionary, default_value)
        self.set_values = set_values

    def prompt (self):
        result = self.description + ':\n'
        for index, (_, label) in enumerate (self.set_values):
            result += '%2d - %s\n' % (index + 1, label)
        result += '? '
        return result
    
    def parse_string (self, string):
        return self.set_values [int (string) - 1][0]

    def validate_value (self, value):
        return value in [v for v, _ in self.set_values]

class Config:
    def __init__ (self, parameters):
        self.parameters_as_list = copy.copy (parameters)
        self.parameters_as_dict = dict ([(p.name, p) for p in parameters])

    def load_from_yaml_file (self, filename):
        file_object = open (filename, 'r')
        dictionary = yaml.load (file_object)
        file_object.close ()
        pause = False
        for p in self.parameters_as_list:
            result = p.load_from_dictionary (dictionary)
            pause = pause or result
        if pause:
            raw_input ('Press ENTER to continue')

    def ask_user (self):
        for p in self.parameters_as_list:
            p.ask_user ()

    def to_dictionary (self):
        result = {}
        return result
    
    def __getattr__ (self, name):
        try:
            p = self.parameters_as_dict [name]
        except KeyError:
            raise AttributeError (name)
        if not p.has_value:
            raise AttributeError (name)
        return p.value

    def __str__ (self):
        result = ""
        for p in self.parameters_as_list:
            if p.has_value:
                for b in p.path_in_dictionary:
                    result += b + ' : '
                result += p.name + ' : ' + str (p.value) + '\n'
        return result

