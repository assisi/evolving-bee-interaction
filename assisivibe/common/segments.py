#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

SGT_VIBRATION  = 1
SGT_AIRFLOW    = 2
SGT_NO_STIMULI = 3

class Segment:
    '''
    A segment has a dual role:

    1) it describes what a CASU can do during
    a chromosome evaluation,

    2) it describes part of a video recording. The video recording is processed according to a certain number of region-of-interest.
    '''
    DEFAULT_USAGE = {
        SGT_VIBRATION  : True,
        SGT_AIRFLOW    : False,
        SGT_NO_STIMULI : False}

    def __init__ (self, duration, type = None, frame_processing_function = None, casu_index = -1, description = None, first_frame = -1, last_frame = -1, pulses = None):
        self.duration = duration
        self.type = type
        self.frame_processing_function = frame_processing_function
        self.casu_index = casu_index
        self.description = description
        self.first_frame = first_frame
        self.last_frame = last_frame
        self.pulses = pulses

    def compute_first_last_frame (self, frames_per_second, current_frame):
        self.first_frame = int (current_frame)
        self.last_frame = int (current_frame + int (self.duration * frames_per_second) - 1)
        return self.last_frame

    def execute (self, casu, chromosome = None, run_vibration_model = None):
        if self.type == SGT_VIBRATION:
            run_vibration_model (chromosome, casu, self.duration)
            casu.speaker_standby ()
        elif self.type == SGT_AIRFLOW:
            casu.set_airflow_intensity (1)
            time.sleep (self.duration)
            casu.airflow_standby ()
        elif self.type == SGT_NO_STIMULI:
            time.sleep (self.duration)
        else:
            raise StandardError ("Invalid segment type") 

    def previous_frame (self, rows):
        return [r [1 + 2 * self.casu_index] for r in rows [self.first_frame:(self.last_frame + 1)]]

    def background_frame (self, rows):
        return [r [2 * self.casu_index] for r in rows [self.first_frame:(self.last_frame + 1)]]

    def get_description (self):
        '''
        Return a human readable description of this segment.
        '''
        if self.description is None:
            return SEGMENT_TYPE_2_STRING [self.type]
        else:
            return self.description

    def to_dict (self):
        result = {'duration' : self.duration}
        if self.type is not None:
            result ['type'] = SEGMENT_TYPE_2_STRING [self.type]
        if self.frame_processing_function is not None:
            result ['frame_processing_function'] = self.frame_processing_function
        if self.casu_index != -1:
            result ['casu_index'] = self.casu_index
        if self.description is not None:
            result ['description'] = self.description
        if self.first_frame != -1:
            result ['first_frame'] = self.first_frame
        if self.last_frame != -1:
            result ['last_frame'] = self.last_frame
        return result

    def filter (self, frame_filter):
        '''
        Return a tuple representing a frame interval based on this segment first and last frames and the given frame filter.
        '''
        if frame_filter == (None, None):
            return (self.first_frame, self.last_frame)
        elif frame_filter [0] == None:
            return (self.last_frame - frame_filter [1] + 1, self.last_frame)
        elif frame_filter [1] == None:
            return (self.first_frame, self.first_frame + frame_filter [0] - 1)

    def __repr__ (self):
        return '%d %d %s %d %d' % (self.duration, self.type, str (self.frame_processing_function), self.first_frame, self.last_frame)
    
    def __str__ (self):
        return '%fs %s %s [%d, %d[' % (
            self.duration,
            SEGMENT_TYPE_2_STRING [self.type],
            str (self.frame_processing_function),
            self.first_frame,
            self.last_frame)


class Segments (list):
    def __init__ (self, segment_data):
        for sd in segment_data:
            duration = sd ['duration']
            stype = sd.get ('type')
            if stype is not None:
                type = STRING_2_SEGMENT_TYPE [stype]
            else:
                type = None
            frame_processing_function = sd.get ('frame_processing_function')
            casu_index = sd.get ('casu_index', -1)
            description = sd.get ('description')
            first_frame = sd.get ('first_frame', -1)
            last_frame = sd.get ('last_frame', -1)
            pulses = sd.get ('pulses', None)
            sgt = Segment (duration, type, frame_processing_function, casu_index, description, first_frame, last_frame, pulses)
            self.append (sgt)

    def compute_first_last_frames (self, frames_per_second, has_blip):
        current_frame = 1 if has_blip else 0
        for sgt in self:
            current_frame = sgt.compute_first_last_frame (frames_per_second, current_frame)
            current_frame += 1 + (2 if has_blip else 0)

    def total_number_frames (self):
        return self [-1].last_frame + 1

    def execute (self, casu, chromosome, has_blip, frames_per_second):
        def blip_casu ():
            casu.set_diagnostic_led_rgb (0.125, 0, 0)
            time.sleep (2.0 / frames_per_second)
            casu.diagnostic_led_standby ()
        if has_blip:
            blip_casu ()
        for sgt in self:
            sgt.execute (casu, chromosome)
            if has_blip:
                blip_casu ()

# def parse_segments (config):
#     result = []
#     evaluation_proceeding =  config.evaluation_proceeding
#     for ep in evaluation_proceeding:
#         duration = ep ['duration']
#         type = STRING_2_SEGMENT_TYPE [ep ['type']]
#         frame_processing_function = ep.get ('frame_processing_function')
#         column_index = ep.get ('column_index', 0)
#         description = ep.get ('description')
#         sgt = Segment (duration, type, frame_processing_function, column_index, description)
#         result.append (sgt)
#     return result

# def compute_first_last_frames (segments, config):
#     frames_per_second = config.frames_per_second
#     current_frame = 1 if config.has_blip else 0
#     for sgt in segments:
#         current_frame = sgt.compute_first_last_frame (frames_per_second, current_frame)
#         current_frame += 1 if config.has_blip else 0

# def total_number_frames (segments):
#     return segments [-1].last_frame + 1

# def execute (segments, casu, chromosome, has_blip, frames_per_second):
#     def blip_casu ():
#         casu.set_diagnostic_led_rgb (0.125, 0, 0)
#         time.sleep (2.0 / frames_per_second)
#         casu.diagnostic_led_standby ()
#     if has_blip:
#         blip_casu ()
#     for sgt in segments:
#         sgt.execute (casu, chromosome)
#         if has_blip:
#             blip_casu ()

STRING_2_SEGMENT_TYPE = {
    'vibration'  : SGT_VIBRATION,
    'airflow'    : SGT_AIRFLOW,
    'no stimuli' : SGT_NO_STIMULI}

SEGMENT_TYPE_2_STRING = {
    SGT_VIBRATION  : 'vibration',
    SGT_AIRFLOW    : 'airflow',
    SGT_NO_STIMULI : 'no stimuli'}

CIRCULAR_ARENA_VIDEO_SEGMENTS = Segments ([
    {'duration' : 30}])
