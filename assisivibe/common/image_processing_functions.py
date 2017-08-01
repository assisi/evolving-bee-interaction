#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This module contains the image processing functions that are used by the evolutionary algorithm, and by the tools that analyse the behaviour of bees.


def bee_pixels_IF_bees_AND_no_movement_ONLY_IN_active (config, active_roi_index, row):
    """
    In this function we:

    1) add the number of bee pixels if in the active CASU ROI there is no movement and there are enough bees.

    This function can be used in arenas with any number of CASUs/ROIs.
    """
    column_active_previous = active_roi_index * 2 + 1
    column_active_background = active_roi_index  * 2
    return \
        + (row [column_active_background]  if row [column_active_background]  > config.pixel_count_background_threshold and row [column_active_previous]  < config.pixel_count_previous_frame_threshold else 0)

def frames_IF_no_movement_ONLY_IN_active (config, active_roi_index, row):
    """
    In this function we:

    1) add the number of frames if in the active CASU ROI there is no movement.

    This function can be used in arenas with any number of CASUs/ROIs.
    """
    column_active_previous = active_roi_index * 2 + 1
    return \
        +(1 if row [column_active_previous] < config.pixel_count_previous_frame_threshold else 0)

def frames_IF_no_movement_IN_active_passive (config, active_roi_index, row):
    """
    In this function we:

    1) add the number of frames if in the active CASU ROI there is no movement;

    2) subtract the number of frames if in the passive CASU ROI there is no movement.

    This function requires an arena with two CASUs.
    """
    column_active_previous = active_roi_index * 2 + 1
    column_passive_previous = (1 - active_roi_index) * 2 + 1
    return \
        +(1 if  row [column_active_previous]  < config.pixel_count_previous_frame_threshold else 0) \
        -(1 if  row [column_passive_previous] < config.pixel_count_previous_frame_threshold else 0)

def bee_pixels_IF_bees_AND_no_movement_IN_active_passive (config, active_roi_index, row):
    """
    In this function we:

    1) add the number of bee pixels if in the active CASU ROI there is no movement and if there are enough bees;

    2) subtract the number of bee pixels if in the passive CASU ROI there is no movement and if there are enough bees.

    This function requires an arena with two CASUs.
    """
    column_active_previous = active_roi_index * 2 + 1
    column_passive_previous = (1 - active_roi_index) * 2 + 1
    column_active_background = active_roi_index  * 2
    column_passive_background = (1 - active_roi_index) * 2
    return \
        + (row [column_active_background]  if row [column_active_background]  > config.pixel_count_background_threshold and row [column_active_previous]  < config.pixel_count_previous_frame_threshold else 0) \
        - (row [column_passive_background] if row [column_passive_background] > config.pixel_count_background_threshold and row [column_passive_previous] < config.pixel_count_previous_frame_threshold else 0)

def frames_IF_bees_AND_no_movement_IN_active_passive (config, active_roi_index, row):
    """
    In this function we:

    1) add the number of frames if in the active CASU ROI there is no movement and if there are enough bees;

    2) subtract the number of frames if in the passive CASU ROI there is no movement and if there are enough bees.

    This function requires an arena with two CASUs.
    """
    column_active_previous = active_roi_index * 2 + 1
    column_passive_previous = (1 - active_roi_index) * 2 + 1
    column_active_background = active_roi_index  * 2
    column_passive_background = (1 - active_roi_index) * 2
    return \
        + 1 if row [column_active_background]  > config.pixel_count_background_threshold and row [column_active_previous]  < config.pixel_count_previous_frame_threshold else 0 \
        - 1 if row [column_passive_background] > config.pixel_count_background_threshold and row [column_passive_previous] < config.pixel_count_previous_frame_threshold else 0

def percentage_bees_IF_bees_ONLY_IN_active (config, active_roi_index, row):
    '''
    In this function we:

    divide the number of moving bee pixels by the number of bee pixels in the active CASU ROI.

    This function requires an arena with at least one CASU.
    '''
    column_active_previous = active_roi_index * 2 + 1
    column_active_background = active_roi_index  * 2
    return float (row [column_active_previous]) / row [column_active_background] if row [column_active_background] > config.pixel_count_background_threshold else 0

# unit of the image processing functions range
UIPF_FRAME = 1
UIPF_BEE_PIXEL = 2
UIPF_PERCENTAGE = 3

class Function:
    def __init__ (self, function, code, description, minimum_number_ROIs, unit, range_minmax):
        self.function = function
        self.code = code
        self.description = description
        self.minimum_number_ROIs = minimum_number_ROIs
        self.unit = unit
        self.range_minmax = range_minmax

F_m_a = Function (
    function = frames_IF_no_movement_ONLY_IN_active,
    code = 'F_m_a',
    description = 'calculates the number of frames where is no movement in the active CASU region of interest.',
    minimum_number_ROIs = 1,
    unit = UIPF_FRAME,
    range_minmax = (0, 1))
F_m_ap = Function (
    function = frames_IF_no_movement_IN_active_passive,
    code = 'F_m_ap',
    description = 'if in the current frame there is no movement in the active CASU region of interest, it adds one; if in the current frame there is no movement in the passive CASU region of interest, it subtracts one.',
    minimum_number_ROIs = 2,
    unit = UIPF_FRAME,
    range_minmax = (-1, 1))
F_bm_ap = Function (
    function = frames_IF_bees_AND_no_movement_IN_active_passive,
    code = 'F_bm_ap',
    description = 'if in the current frame there is no movement and bees in the active CASU region of interest, it adds one; if in the current frame there is no movement and bees in the passive CASU region of interest, it subtracts one.',
    minimum_number_ROIs = 2,
    unit = UIPF_FRAME,
    range_minmax = (-1, 1))
B_bm_a = Function (
    function = bee_pixels_IF_bees_AND_no_movement_ONLY_IN_active,
    code = 'B_bm_a',
    description = 'if in the current frame there is no movement and bees in the active CASU region of interest, it adds the bee pixels in this region of interest.',
    minimum_number_ROIs = 1,
    unit = UIPF_BEE_PIXEL,
    range_minmax = (0, 1))
B_bm_ap = Function (
    function = bee_pixels_IF_bees_AND_no_movement_IN_active_passive,
    code = 'B_bm_ap',
    description = 'if in the current frame there is no movement and bees in the active CASU region of interest, it adds the bee pixels in this region of interest; if in the current frame there is no movement and bees in the passive CASU region of interest, it subtracts the bee pixels in this region of interest.',
    minimum_number_ROIs = 2,
    unit = UIPF_BEE_PIXEL,
    range_minmax = (-1, 1))
PB_m_a = Function (
    function = percentage_bees_IF_bees_ONLY_IN_active,
    code = '%B_m_a',
    description = 'if in the current frame there are bees, then it return the ratio between the number of pixels that are different from the previous frame over the number of pixels that are different from the background frame',
    minimum_number_ROIs = 1,
    unit = UIPF_PERCENTAGE,
    range_minmax = (0, 1))

FUNCTIONs = [F_m_a, F_m_ap, F_bm_ap, B_bm_a, B_bm_ap, PB_m_a]

STRING_2_OBJECT = {
    'frames_IF_no_movement_ONLY_IN_active'                 : F_m_a    ,
    'frames_with_no_movement_active_casu_roi'              : F_m_a    ,
    'F_m_a'                                                : F_m_a    ,
    'frames_IF_no_movement_IN_active_passive'              : F_m_ap   ,
    'frames_with_no_movement_active_passive_casu_rois'     : F_m_ap   ,
    'F_m_ap'                                               : F_m_ap   ,
    'frames_IF_bees_AND_no_movement_IN_active_passive'     : F_bm_ap  ,
    'bee_pixels_IF_bees_AND_no_movement_ONLY_IN_active'    : B_bm_a   ,
    'B_bm_a'                                               : B_bm_a   ,
    'bee_pixels_IF_bees_AND_no_movement_IN_active_passive' : B_bm_ap  ,
    'penalize_passive_casu'                                : B_bm_ap  ,
    'B_bm_ap'                                              : B_bm_ap  ,
    'percentage_bees_IF_bees_ONLY_IN_active'               : PB_m_a   ,
    '%B_m_a'                                               : PB_m_a   ,
    }
OBJECT_2_CODE = dict ([(f, f.code) for f in FUNCTIONs])

def compute (config, active_roi_index, iterator):
    result = 0
    function = STRING_2_OBJECT [config.image_processing_function].function
    for row in iterator:
        result += function (config, active_roi_index, row)
    return int (result)
