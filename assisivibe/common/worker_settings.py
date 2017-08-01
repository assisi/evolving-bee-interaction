#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import stat
import yaml
import zmq

import assisipy.deploy
import assisipy.assisirun
import assisipy.collect_data

import zmq_sock_utils

class WorkerSettings:
    """
    Worker settings used by the master program to deploy the workers.
    These settings specify the CASU that the worker will control,
    the ZMQ address where the worker will listen for commands from the master,
    and the parameters of the RTC file.
    """
    def __init__ (self, dictionary):
        self.casu_number = dictionary ['casu_number']
        self.wrk_addr    = dictionary ['wrk_addr']
        self.pub_addr    = dictionary ['pub_addr']
        self.sub_addr    = dictionary ['sub_addr']
        self.msg_addr    = dictionary ['msg_addr']

    def key (self):
        return 'casu-%03d' % (self.casu_number)

    def to_dep (self, controller, extra):
        return (
            self.key () ,
            {
                'controller' : controller
              , 'extra'      : extra
              , 'args'       : [str (self.casu_number), 'tcp://*:%s' % (self.wrk_addr.split (':') [2])]
              , 'hostname'   : self.wrk_addr.split (':') [1][2:]
              , 'user'       : 'assisi'
              , 'prefix'     : 'pedro/patvibe'
              , 'results'    : []
            })

    def to_arena (self):
        return (
            self.key () ,
            {
                'pub_addr' : self.pub_addr
              , 'sub_addr' : self.sub_addr
              , 'msg_addr' : self.msg_addr
            })

    def connect_to_worker (self):
        """
        Connect to the worker and return the socket.
        """
        context = zmq.Context ()
        print ("Connecting to worker at %s responsible for casu #%d..." % (self.wrk_addr, self.casu_number))
        socket = context.socket (zmq.REQ)
        socket.connect (self.wrk_addr)
        return socket

    def __str__ (self):
        return 'casu_number : %d , wrk_addr : %s , pub_addr : %s , sub_addr : %s , msg_addr : %s' % (
            self.casu_number, self.wrk_addr, self.pub_addr, self.sub_addr, self.msg_addr)

class BasicWorkerStub:
    def __init__ (self, casu_number, socket):
        self.casu_number = casu_number
        self.socket = socket
        self.in_use = False

    def key (self):
        return 'casu-%03d' % (self.casu_number)

    def __repr__ (self):
        return '(%d %s %s)' % (self.casu_number, self.socket.__repr__ (), self.in_use.__repr__ ())

def load_worker_settings (filename):
    """
    Return a list with the worker settings loaded from a file with the given name.
    """
    print ("Loading worker settings...")
    file_object = open (filename, 'r')
    dictionary = yaml.load (file_object)
    file_object.close ()
    list_worker_settings = [
        WorkerSettings (dictionary ['worker-%02d' % (index)])
        for index in xrange (1, dictionary ['number_workers'] + 1)]
    print ("Loaded worker settings.")
    return list_worker_settings

def deploy_workers (filename, controller, extra):
    print ('\n\n* ** Worker Apps Launch')
    # load worker settings
    list_worker_settings = load_worker_settings (filename)
    # create assisi file
    fp_assisi = open ('tmp/workers.assisi', 'w')
    yaml.dump ({'arena' : 'workers.arena'}, fp_assisi, default_flow_style = False)
    yaml.dump ({'dep' : 'workers.dep'}, fp_assisi, default_flow_style = False)
    fp_assisi.close ()
    print ("Created assisi file")
    # create dep file
    fp_dep = open ('tmp/workers.dep', 'w')
    yaml.dump ({'arena' : dict ([ws.to_dep (controller, extra) for ws in list_worker_settings])}, fp_dep, default_flow_style = False)
    fp_dep.close ()
    print ("Created dep file")
    # create arena file
    fp_arena = open ('tmp/workers.arena', 'w')
    yaml.dump ({'arena' : dict ([ws.to_arena () for ws in list_worker_settings])}, fp_arena, default_flow_style = False)
    fp_arena.close ()
    print ("Created arena file")
    # deploy the workers
    d = assisipy.deploy.Deploy ('tmp/workers.assisi')
    d.prepare ()
    d.deploy ()
    ar = assisipy.assisirun.AssisiRun ('tmp/workers.assisi')
    ar.run ()
    print ("Workers have finished")

def connect_workers (list_worker_settings, worker_stub_constructor):
    '''
    Connect to workers and return a dictionary with each casu number associated with a worker stub.
    '''
    return dict (
        [(ws.casu_number, worker_stub_constructor (ws.casu_number, ws.connect_to_worker ()))
        for ws in list_worker_settings])

def convert_dummy_workers_stub (list_worker_settings):
    return dict ([(ws.casu_number, BasicWorkerStub (ws.casu_number, None))
                  for ws in list_worker_settings])

def collect_data_from_workers (list_worker_settings, destination):
    dc = assisipy.collect_data.DataCollector ('tmp/workers.assisi', logpath = destination)
    dc.collect ()
    for ws in list_worker_settings:
        try:
            os.makedirs (os.path.join (destination, ws.key ()))
        except:
            pass
        source = os.path.join (destination, os.path.join ('data_workers/arena', ws.key ()))
        for filename in os.listdir (source):
            new = os.path.join (os.path.join (destination, ws.key ()), filename)
            os.rename (os.path.join (source, filename), new)
            os.chmod (new, stat.S_IREAD)
        os.rmdir (source)
    os.rmdir (os.path.join (destination, 'data_workers/arena'))
    os.rmdir (os.path.join (destination, 'data_workers'))
