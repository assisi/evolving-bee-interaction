#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import csv
import os
import re
import subprocess

def find_app (app):
    command = "which " + app
    process = subprocess.Popen (command, stdout = subprocess.PIPE, shell = True)
    out, _ = process.communicate ()
    if process.returncode != 0:
        print ('This computer does not have application', app)
        return '/bin/true'
    else:
        return out [:-1]

def remove_tmp_directory (directory):
    for tmp_file in os.listdir (directory):
        os.remove (tmp_file)
    os.rmdir (directory)

CONVERT_BIN_FILENAME = find_app ("convert")

COMPARE_BIN_FILENAME = find_app ("compare")

GNUPLOT_BIN_FILENAME = find_app ("gnuplot")

FFMPEG_BIN_FILENAME = find_app ("ffmpeg")

AVCONV_BIN_FILENAME = find_app ("avconv")

R_BIN_FILENAME = find_app ("R")

DISPLAY_BIN_FILENAME = find_app ("display")

GST_LAUNCH = find_app ('gst-launch-0.10')

XTERM = find_app ('xterm')

PLOT_GAP_SPINE_LIM = 0.1

def is_answer_yes (prompt):
    '''
    Presents a prompt to the user to make a yes or no question.
    Returns true if the user answered yes or y.
    '''
    while True:
        answer = raw_input (prompt + ' (y/n)? ').upper ()
        if answer == 'YES' or answer == 'Y':
            return True
        elif answer == 'NO' or answer == 'N':
            return False
        else:
            print ('Invalid answer!')

def set_plot_lim (function, min_lim, max_lim, axes_length):
    adjust = (max_lim - min_lim) * PLOT_GAP_SPINE_LIM / (axes_length - 2 * PLOT_GAP_SPINE_LIM)
    function ([min_lim - adjust, max_lim + adjust])

def add_ticks (get_ticks, set_ticks, new_ticks):
    '''
    Add new ticks if not present.
    '''
    current_ticks = get_ticks ()
    for atick in new_ticks:
        if atick not in current_ticks:
            current_ticks += [atick]
    set_ticks (current_ticks)

def load_csv (filename, has_header, constructor = None, **kargs):
    '''
    Read the contents of a csv file.  Each row is passed to the given constructor. Return a list of instances.
    '''
    fpr = open (filename, 'r')
    freader = csv.reader (fpr, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar = '"')
    if has_header:
        freader.next ()
    if constructor is None:
        result = [row for row in freader]
    else:
        result = [constructor (row, **kargs) for row in freader]
    fpr.close ()
    return result


def open_csv_writer (filename):
    fpw = open (filename, 'w')
    fwriter = csv.writer (fpw, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar = '"')
    return (fpw, fwriter)

def list_runs ():
    '''
    Return a list of the run numbers.  Each run number corresponds to folder named 'run-xxx'.
    '''
    regex = re.compile ('^run-[0123456789]{3}$')
    for filename in os.listdir ('.'):
        if regex.match (filename):
            run_number = int (filename [4:7])
            yield run_number

def record_video (video_filename, number_frames, frames_per_second, crop_left, crop_right, crop_top, crop_bottom, debug = False):
    command =  [
        GST_LAUNCH,
        '--gst-plugin-path=/usr/local/lib/gstreamer-0.10/',
        '--gst-plugin-load=libgstaravis-0.4.so',
        #'--verbose',
        '--quiet',
        'aravissrc', 'num-buffers=%d' % (number_frames), '!',
        'video/x-raw-yuv,width=2048,height=2048,framerate=%d/1' % (frames_per_second), '!',
        'videocrop', 'left=%d' % (crop_left), 'right=%d' % (crop_right), 'top=%d' % (crop_top), 'bottom=%d' % (crop_bottom), '!',
        'jpegenc', '!',
        'avimux', 'name=mux', '!',
        'filesink', 'location=%s' % (video_filename)
        ]
    if debug:
        import arena
        print
        print ('Recording a video with %d frames at %d frames per second.' % (number_frames, frames_per_second))
        print ('Frame resolution is %dx%d.' % (arena.CAMERA_RESOLUTION_X - crop_right - crop_left, arena.CAMERA_RESOLUTION_Y - crop_top - crop_bottom))
        print ('Full command is:')
        print (' '.join (command))
        print
    return subprocess.Popen (command)

def split_video (video_filename, number_frames, frames_per_second, output_template):
    command = [
        FFMPEG_BIN_FILENAME,
        '-i', video_filename,
        '-r', '%f' % (frames_per_second),
        '-loglevel', 'error',
        '-frames', '%d' % (number_frames),
        '-f', 'image2',
        output_template
        ]
    return subprocess.Popen (command)

def casu_freader (log_path, casu_number):
    '''
    Return an iterator that returns CSV rows of the given CASU logs.

    Logs are assumed to be in folders named casu-XXX. In these folders there should be only CASU logs.
    The filenames of these logs should contain a date with year, month, day, hour, minute and second in this order.
    '''
    casu_path = os.path.join (log_path, 'casu-%03d' % (casu_number))
    if os.path.exists (casu_path):
        list_files = [filename for filename in os.listdir (casu_path)]
        list_files.sort ()
        for filename in list_files:
            fd = open (os.path.join (casu_path, filename), 'r')
            freader = csv.reader (fd, delimiter = ';', quoting = csv.QUOTE_NONE)
            for line in freader:
                yield line
            fd.close ()
    else:
        print (casu_path, 'does not exist')
