#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
A tool to help inspect (bee) frames, and select an RoI graphically
run with "-h" to see options

the program requires an image as parameter.

apt-get install python-pyside.qtcore python-pyqtgraph python-pyside.qtopengl python-pyside.qtsvg

'''

from __future__ import print_function

from PySide import QtCore
from PySide import QtGui
from PySide.QtCore import Qt

import argparse
import functools
import numpy
import os.path
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageOps
import pyqtgraph
import PySide.QtGui
import subprocess
import sys
import yaml


class BaseROIPicker (PySide.QtGui.QDialog):
    '''
    The basic region-of-interest picker has a place holder for the image, the button to toggle between the entire image and the mask, the button to accept the data, and the are to enter the properties of the ROI.
    '''
    def __init__ (self, background_image_path):
        '''
        '''
        PySide.QtGui.QDialog.__init__ (self)
        self.background_image_path = background_image_path
        self.image_item = None
        self.spinners = {}
        self._setup_window ()
        if background_image_path is not None:
            self._load_background_image ()
        self.block = False
        self.highlighted = False
        self.setMinimumSize (1024, 768)

    def _setup_window (self):
        dialog_layout = PySide.QtGui.QHBoxLayout ()
        self.setLayout (dialog_layout)
        # widget with the background image
        self.widg_img = pyqtgraph.GraphicsLayoutWidget()
        self.im_vb    = self.widg_img.addViewBox (row = 1, col = 1)
        dialog_layout.addWidget (self.widg_img)
        # widget with ROI form and buttons
        splitter2 = PySide.QtGui.QSplitter ()
        splitter2.setOrientation (PySide.QtCore.Qt.Vertical)
        dialog_layout.addWidget (splitter2)
        # widget with ROI form
        self._ROI_properties_form = PySide.QtGui.QFormLayout ()
        frame = PySide.QtGui.QFrame ()
        frame.setLayout (self._ROI_properties_form)
        splitter2.addWidget (frame)
        # widget with buttons
        widg_btns = PySide.QtGui.QWidget()
        button_highlight_ROI = QtGui.QPushButton ("&highlight ROI")
        button_highlight_ROI.clicked.connect (self._highlight_ROI)
        button_OK = QtGui.QPushButton("&OK")
        button_OK.clicked.connect (self._ok)
        btn_lay = QtGui.QHBoxLayout()
        btn_lay.addWidget (button_highlight_ROI)
        btn_lay.addWidget (button_OK)
        widg_btns.setLayout(btn_lay)
        splitter2.addWidget(widg_btns)

    def set_background_image_path (self, background_image_path):
        self.background_image_path = background_image_path
        self._load_background_image ()

    def _load_background_image (self):
        if self.image_item != None:
            self.im_vb.removeItem (self.image_item)
        image = PIL.Image.open (self.background_image_path)
        # we have to flip the image horizontally
        self.imgdata = numpy.array (image.rotate (270))
        self._prep_mask ()
        self.image_item = pyqtgraph.ImageItem (self.imgdata)
        self.im_vb.addItem (self.image_item)
        self.im_vb.setAspectLocked (True)

    def _prep_mask (self):
        '''
        rather than generate copy every time, generate a mask on loading
        image.
        '''
        w, h, d = self.imgdata.shape
        self.mask = numpy.zeros ((w, h, 4), dtype=int) # needs to be 4layer to be RGBa
        # set the relevant coordinates in the 4th layer (alpha)
        # hmm, it seems annoying. So lets just make a copy to display.
        for layer in [0,1,2]:
            self.mask[:,:,layer] = self.imgdata[:,:,layer]

    def roi_widget_update (self):
        pass
    def _highlight_ROI (self):
        self.highlighted = not self.highlighted
        if self.highlighted:
            # mask all pixels
            self.mask [:,:,3] = int (0.4 * 255)
            self.build_mask ()
            self.image_item.setImage (self.mask)
        else:
            self.image_item.setImage (self.imgdata)
    def _ok (self):
        self.close ()

    def _add_spinner (self, label, default_value, callback):
        spin = PySide.QtGui.QSpinBox ()
        spin.setMinimum (0)
        spin.setMaximum (2048)
        spin.setValue (default_value)
        spin.valueChanged.connect (callback)
        self.spinners [label] = spin
        self._ROI_properties_form.addRow (label, spin)
        

    def new_circle_ROI (self, default_center_x, default_center_y, default_radius, key_center_x, key_center_y, key_radius):
        result = pyqtgraph.CircleROI (
            pos = (default_center_x - default_radius, default_center_y - default_radius),
            size = 2 * default_radius,
        )
        self.im_vb.addItem (result)
        result.sigRegionChanged.connect (
            functools.partial (self.update_spinners_4_circle_ROI, key_center_x, key_center_y, key_radius))
        for key_spinner, default_value in zip (
                [key_center_x, key_center_y, key_radius],
                [default_center_x, default_center_y, default_radius]):
            self._add_spinner (
                key_spinner,
                default_value,
                functools.partial (self.update_circle_ROI_4_spinners, key_center_x, key_center_y, key_radius, result))
        return result

    def new_rect_ROI (self, default_center_x, default_center_y, default_width, default_height, key_center_x, key_center_y, key_width, key_height):
        result = pyqtgraph.RectROI (
            pos = (default_center_x - default_width / 2, default_center_y - default_height / 2),
            size = (default_width, default_height),
            sideScalers = True
        )
        self.im_vb.addItem (result)
        result.sigRegionChanged.connect (
            functools.partial (self.update_spinners_4_rect_ROI, key_center_x, key_center_y, key_width, key_height))
        for key_spinner, default_value in zip (
                [key_center_x, key_center_y, key_width, key_height],
                [default_center_x, default_center_y, default_width, default_height]):
            self._add_spinner (
                key_spinner,
                default_value,
                functools.partial (self.update_rect_ROI_4_spinners, key_center_x, key_center_y, key_width, key_height, result))
        return result

    def update_spinners_4_rect_ROI (self, key_center_x, key_center_y, key_width, key_height, roi):
        if self.block:
            return
        self.block = True
        x, y = roi.pos ()
        w, h = roi.size ()
        self.spinners [key_center_x].setValue (x + w // 2)
        self.spinners [key_center_y].setValue (y + h // 2)
        self.spinners [key_width].setValue (w)
        self.spinners [key_height].setValue (h)
        self.block = False

    def update_spinners_4_circle_ROI (self, key_center_x, key_center_y, key_radius, roi):
        if self.block:
            return
        self.block = True
        x, y = roi.pos ()
        w, h = roi.size ()
        r = int (w / 2)
        self.spinners [key_center_x].setValue (x + r)
        self.spinners [key_center_y].setValue (y + r)
        self.spinners [key_radius].setValue (r)
        self.block = False

    def update_rect_ROI_4_spinners (self, key_center_x, key_center_y, key_width, key_height, roi, _value):
        if self.block:
            return
        self.block = True
        x = self.spinners [key_center_x].value ()
        y = self.spinners [key_center_y].value ()
        w = self.spinners [key_width].value ()
        h = self.spinners [key_height].value ()
        roi.setPos ((x - w // 2, y - h // 2), update = False)
        roi.setSize ((w, h), update = True)
        self.block = False

    def update_circle_ROI_4_spinners (self, key_center_x, key_center_y, key_radius, roi, _value):
        if self.block:
            return
        self.block = True
        x = self.spinners [key_center_x].value ()
        y = self.spinners [key_center_y].value ()
        r = self.spinners [key_radius].value ()
        roi.setPos ((x - r, y - r), update = False)
        roi.setSize ((2 * r, 2 * r), update = True)
        self.block = False

    def mask_rect (self, center_x, center_y, width, height, color = 255):
        w, h, _d = self.imgdata.shape
        for x in xrange (- width // 2, width // 2):
            for y in xrange (- height // 2, height // 2):
                if 0 <= center_x + x < w and 0 <= center_y + y < h:
                    self.mask [center_x + x, center_y + y, 3] = color

    def mask_circle (self, cx, cy, r, color = 255):
        w, h, _d = self.imgdata.shape
        for x in xrange (- r, + r):
            for y in xrange ( - r, + r):
                if x ** 2 + y ** 2 <= r ** 2 and 0 <= x + cx < w and 0 <= y + cy < h:
                    self.mask [cx + x, cy + y, 3] = color

    def draw_rect (self, draw, center_x, center_y, width, height, colour = 'white'):
        w, h, _d = self.imgdata.shape
        # we have to flip the image horizontally
        draw.rectangle (((center_x - width // 2, h - (center_y + height // 2) - 1), (center_x + width // 2, h - (center_y - height // 2) - 1)), fill = colour)

    def draw_circle (self, draw, center_x, center_y, radius, colour = 'white'):
        w, h, _d = self.imgdata.shape
        draw.ellipse (((center_x - radius, h - (center_y + radius) - 1), (center_x + radius, h - (center_y - radius) - 1)), fill = colour)

    def save_rect_mask_image (self, center_x, center_y, width, height, image_path):
        w, h, _d = self.imgdata.shape
        mask_roi = PIL.Image.new ('L', (w, h), 'black')
        self.draw_rect (PIL.ImageDraw.Draw (mask_roi), center_x, center_y, width, height)
        mask_roi.save (image_path)

    def save_circle_mask_image (self, center_x, center_y, radius, image_path):
        w, h, _d = self.imgdata.shape
        mask_roi = PIL.Image.new ('L', (w, h), 'black')
        self.draw_circle (PIL.ImageDraw.Draw (mask_roi), center_x, center_y, radius)
        mask_roi.save (image_path)

class CircularArenaROIPicker (BaseROIPicker):
    '''
    A region-of-interest picker that allows the selection of one circular region
    '''
    ROIP_CENTER_X = 'center x'
    ROIP_CENTER_Y = 'center y'
    ROIP_RADIUS = 'radius'
    def __init__ (self, background_image_path, center_x = 500, center_y = 500, radius = 125):
        BaseROIPicker.__init__ (self, background_image_path)
        self.roi = self.new_circle_ROI (
            center_x, center_y, radius,
            CircularArenaROIPicker.ROIP_CENTER_X,
            CircularArenaROIPicker.ROIP_CENTER_Y,
            CircularArenaROIPicker.ROIP_RADIUS)

    def _get_roi_properties (self):
        return (
            self.spinners [CircularArenaROIPicker.ROIP_CENTER_X].value (),
            self.spinners [CircularArenaROIPicker.ROIP_CENTER_Y].value (),
            self.spinners [CircularArenaROIPicker.ROIP_RADIUS].value ()
            )

    def build_mask (self):
        cx, cy, r = self._get_roi_properties ()
        w, h, d = self.imgdata.shape
        for x in xrange (- r, + r):
            for y in xrange ( - r, + r):
                if x ** 2 + y ** 2 <= r ** 2 and 0 <= x + cx < w and 0 <= y + cy < h:
                    self.mask [cx + x, cy + y, 3] = 255

    def create_mask_images (self, images_folder):
        '''
        Create the image masks.
        '''
        w, h, d = self.imgdata.shape
        mask_roi = PIL.Image.new ('L', (w, h), 'black')
        cx, cy, r = self._get_roi_properties ()
        draw = PIL.ImageDraw.Draw (mask_roi)
        # we have to flip the image horizontally
        draw.ellipse (((cx - r, h - (cy + r) - 1), (cx + r, h - (cy - r) - 1)), fill = 'white')
        mask_roi.save (os.path.join (images_folder, 'Mask-0.jpg'))

    def create_region_of_interests_image (self, images_folder):
        '''
        Not working properly...
        '''
        w, h, d = self.imgdata.shape
        cx, cy, r = self._get_roi_properties ()
        base_image = PIL.Image.open (self.background_image_path).convert (mode = 'RGBA')
        roi_image = PIL.Image.new ('RGBA', base_image.size, (255, 255, 255, 0))
        draw = PIL.ImageDraw.Draw (roi_image)
        # we have to flip the image horizontally
        draw.ellipse (((cx - r, h - (cy + r) - 1), (cx + r, h - (cy - r) - 1)), fill = (255,0,0,127))
        out = PIL.Image.alpha_composite (base_image, roi_image)
        out.save (os.path.join (images_folder, 'Region-of-Interests.jpg'))

    def write_properties (self, images_folder):
        w, h, d = self.imgdata.shape
        cx, cy, r = self._get_roi_properties ()
        data = {
            'arena_center_x' : cx,
            'arena_center_y' : h - cy - 1,
            'arena_radius' : r
            }
        with open (os.path.join (images_folder, "roi.properties"), 'w') as fp:
            yaml.dump (data, fp, default_flow_style = False)
            fp.close ()

class TwoCircularArenasROIPicker (BaseROIPicker):
    '''
    A region-of-interest picker that allows the selection of two circular regions.
    '''
    ROIP_1_CENTER_X = 'active ROI center x'
    ROIP_1_CENTER_Y = 'active ROI center y'
    ROIP_1_RADIUS = 'active ROI radius'
    ROIP_2_CENTER_X = 'passive ROI center x'
    ROIP_2_CENTER_Y = 'passive ROI center y'
    ROIP_2_RADIUS = 'passive ROI radius'

    def __init__ (self, background_image_path, center_1_x = 150, center_1_y = 300, center_2_x = 300, center_2_y = 200, radius = 125):
        BaseROIPicker.__init__ (self, background_image_path)
        self.roi1 = self.new_circle_ROI (
            center_1_x, center_1_y, radius,
            TwoCircularArenasROIPicker.ROIP_1_CENTER_X,
            TwoCircularArenasROIPicker.ROIP_1_CENTER_Y,
            TwoCircularArenasROIPicker.ROIP_1_RADIUS)
        self.roi2 = self.new_circle_ROI (
            center_2_x, center_2_y, radius,
            TwoCircularArenasROIPicker.ROIP_2_CENTER_X,
            TwoCircularArenasROIPicker.ROIP_2_CENTER_Y,
            TwoCircularArenasROIPicker.ROIP_2_RADIUS)

    def _get_roi_properties (self):
        return (
            self.spinners [TwoCircularArenasROIPicker.ROIP_1_CENTER_X].value (),
            self.spinners [TwoCircularArenasROIPicker.ROIP_1_CENTER_Y].value (),
            self.spinners [TwoCircularArenasROIPicker.ROIP_1_RADIUS].value (),
            self.spinners [TwoCircularArenasROIPicker.ROIP_2_CENTER_X].value (),
            self.spinners [TwoCircularArenasROIPicker.ROIP_2_CENTER_Y].value (),
            self.spinners [TwoCircularArenasROIPicker.ROIP_2_RADIUS].value ()
            )

    def build_mask (self):
        cx1, cy1, r1, cx2, cy2, r2 = self._get_roi_properties ()
        w, h, d = self.imgdata.shape
        for x in xrange (- r1, + r1):
            for y in xrange ( - r1, + r1):
                if x ** 2 + y ** 2 <= r1 ** 2 and 0 <= x + cx1 < w and 0 <= y + cy1 < h:
                    self.mask [cx1 + x, cy1 + y, 3] = 255
        for x in xrange (- r2, + r2):
            for y in xrange ( - r2, + r2):
                if x ** 2 + y ** 2 <= r2 ** 2 and 0 <= x + cx2 < w and 0 <= y + cy2 < h:
                    self.mask [cx2 + x, cy2 + y, 3] = 255

    def create_mask_images (self, images_folder):
        '''
        Create the image masks.
        '''
        w, h, d = self.imgdata.shape
        cx1, cy1, r1, cx2, cy2, r2 = self._get_roi_properties ()
        for index, (cx, cy, r) in enumerate ([(cx1, cy1, r1), (cx2, cy2, r2)]):
            mask_roi = PIL.Image.new ('L', (w, h), 'black')
            draw = PIL.ImageDraw.Draw (mask_roi)
            # we have to flip the image horizontally
            draw.ellipse (((cx - r, h - (cy + r) - 1), (cx + r, h - (cy - r) - 1)), fill = 'white')
            mask_roi.save (os.path.join (images_folder, 'Mask-%d.jpg' % (index)))

    def create_region_of_interests_image (self, images_folder):
        '''
        Create an image of the background frame with region of interests highlighted.
        '''
        w, h, d = self.imgdata.shape
        base_image = PIL.Image.open (self.background_image_path).convert (mode = 'RGBA')
        roi_image = PIL.Image.new ('RGBA', base_image.size, (255, 255, 255, 0))
        draw = PIL.ImageDraw.Draw (roi_image)
        cx1, cy1, r1, cx2, cy2, r2 = self._get_roi_properties ()
        for (fr, fg, fb, cx, cy, r) in [(255, 0, 0, cx1, cy1, r1), (0, 0, 255, cx2, cy2, r2)]:
            # we have to flip the image horizontally
            draw.ellipse (((cx - r, h - (cy + r) - 1), (cx + r, h - (cy - r) - 1)), fill = (fr,fg,fb,127))
        out = PIL.Image.alpha_composite (base_image, roi_image)
        out.save (os.path.join (images_folder, 'Region-of-Interests.jpg'))

    def write_properties (self, images_folder):
        w, h, d = self.imgdata.shape
        cx1, cy1, r1, cx2, cy2, r2 = self._get_roi_properties ()
        data = {
            'arena_active_center_x' : cx1,
            'arena_active_center_y' : h - cy1 - 1,
            'arena_active_radius' : r1,
            'arena_passive_center_x' : cx2,
            'arena_passive_center_y' : h - cy2 - 1,
            'arena_passive_radius' : r2
            }
        with open (os.path.join (images_folder, "roi.properties"), 'w') as fp:
            yaml.dump (data, fp, default_flow_style = False)
            fp.close ()

class Corridor2Start2GoalROIPicker (BaseROIPicker):
    '''
    A region-of-interest picker that allows the selection of
    two circular regions called goal 1 and goal 2, and of
    two rectangular regions called start 1 and start 2.

    The goal regions-of-interest are circular
    while the start regions-of-interest are rectangular
    '''
    ROIP_START_1_CENTER_X = 'start 1 ROI center x'
    ROIP_START_1_CENTER_Y = 'start 1 ROI center y'
    ROIP_START_1_WIDTH = 'start 1 ROI width'
    ROIP_START_1_HEIGHT = 'start 1 ROI height'
    ROIP_START_2_CENTER_X = 'start 2 ROI center x'
    ROIP_START_2_CENTER_Y = 'start 2 ROI center y'
    ROIP_START_2_WIDTH = 'start 2 ROI width'
    ROIP_START_2_HEIGHT = 'start 2 ROI height'
    ROIP_GOAL_1_CENTER_X = 'goal 1 ROI center x'
    ROIP_GOAL_1_CENTER_Y = 'goal 1 ROI center y'
    ROIP_GOAL_1_RADIUS = 'goal 1 ROI radius'
    ROIP_GOAL_2_CENTER_X = 'goal 2 ROI center x'
    ROIP_GOAL_2_CENTER_Y = 'goal 2 ROI center y'
    ROIP_GOAL_2_RADIUS = 'goal 2 ROI radius'

    def __init__ (self, background_image_path,
                      start_1_center_x = 100, start_1_center_y = 50,
                      start_2_center_x = 300, start_2_center_y = 50,
                      start_width = 200, start_height = 100,
                      goal_1_center_x = 50, goal_1_center_y = 50,
                      goal_2_center_x = 350, goal_2_center_y = 50,
                      goal_radius = 50
                      ):
        BaseROIPicker.__init__ (self, background_image_path)
        self.roi_start_1 = self.new_rect_ROI (
            start_1_center_x, start_1_center_y, start_width, start_height,
            Corridor2Start2GoalROIPicker.ROIP_START_1_CENTER_X,
            Corridor2Start2GoalROIPicker.ROIP_START_1_CENTER_Y,
            Corridor2Start2GoalROIPicker.ROIP_START_1_WIDTH,
            Corridor2Start2GoalROIPicker.ROIP_START_1_HEIGHT)
        self.roi_start_2 = self.new_rect_ROI (
            start_2_center_x, start_2_center_y, start_width, start_height,
            Corridor2Start2GoalROIPicker.ROIP_START_2_CENTER_X,
            Corridor2Start2GoalROIPicker.ROIP_START_2_CENTER_Y,
            Corridor2Start2GoalROIPicker.ROIP_START_2_WIDTH,
            Corridor2Start2GoalROIPicker.ROIP_START_2_HEIGHT)
        self.roi_goal_1 = self.new_circle_ROI (
            goal_1_center_x, goal_1_center_y, goal_radius,
            Corridor2Start2GoalROIPicker.ROIP_GOAL_1_CENTER_X,
            Corridor2Start2GoalROIPicker.ROIP_GOAL_1_CENTER_Y,
            Corridor2Start2GoalROIPicker.ROIP_GOAL_1_RADIUS)
        self.roi_goal_2 = self.new_circle_ROI (
            goal_2_center_x, goal_2_center_y, goal_radius,
            Corridor2Start2GoalROIPicker.ROIP_GOAL_2_CENTER_X,
            Corridor2Start2GoalROIPicker.ROIP_GOAL_2_CENTER_Y,
            Corridor2Start2GoalROIPicker.ROIP_GOAL_2_RADIUS)

    def build_mask (self):
        s1x, s1y, s1w, s1h, s2x, s2y, s2w, s2h, g1x, g1y, g1r, g2x, g2y, g2r = self._get_roi_properties ()
        w, h, d = self.imgdata.shape
        self.mask_rect (s1x, s1y, s1w, s1h)
        self.mask_rect (s2x, s2y, s2w, s2h)
        self.mask_circle (g1x, g1y, g1r)
        self.mask_circle (g2x, g2y, g2r)

    def _get_roi_properties (self):
        return (
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_START_1_CENTER_X].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_START_1_CENTER_Y].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_START_1_WIDTH].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_START_1_HEIGHT].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_START_2_CENTER_X].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_START_2_CENTER_Y].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_START_2_WIDTH].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_START_2_HEIGHT].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_GOAL_1_CENTER_X].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_GOAL_1_CENTER_Y].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_GOAL_1_RADIUS].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_GOAL_2_CENTER_X].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_GOAL_2_CENTER_Y].value (),
            self.spinners [Corridor2Start2GoalROIPicker.ROIP_GOAL_2_RADIUS].value ()
        )

    def create_mask_images (self, images_folder):
        '''
        Create the images masks in the given folder.
        '''
        s1x, s1y, s1w, s1h, s2x, s2y, s2w, s2h, g1x, g1y, g1r, g2x, g2y, g2r = self._get_roi_properties ()
        for index, (cx, cy, w, h) in zip (Corridor2Start2GoalROIPicker.get_indexes_start_masks (), [(s1x, s1y, s1w, s1h), (s2x, s2y, s2w, s2h)]):
            self.save_rect_mask_image (cx, cy, w, h, os.path.join (images_folder, 'Mask-%d.jpg' % (index)))
        for index, (cx, cy, r) in zip (Corridor2Start2GoalROIPicker.get_indexes_goal_masks (), [(g1x, g1y, g1r), (g2x, g2y, g2r)]):
            self.save_circle_mask_image (cx, cy, r, os.path.join (images_folder, 'Mask-%d.jpg' % (index)))

    @staticmethod
    def get_indexes_start_masks ():
        return [0, 1]

    @staticmethod
    def get_indexes_goal_masks ():
        return [2, 3]

    def create_region_of_interests_image (self, images_folder):
        s1x, s1y, s1w, s1h, s2x, s2y, s2w, s2h, g1x, g1y, g1r, g2x, g2y, g2r = self._get_roi_properties ()
        w, h, d = self.imgdata.shape
        base_image = PIL.Image.open (self.background_image_path).convert (mode = 'RGBA')
        roi_image = PIL.Image.new ('RGBA', base_image.size, (255, 255, 255, 0))
        draw = PIL.ImageDraw.Draw (roi_image)
        for (fr, fg, fb, cx, cy, w, h) in [(255, 0, 0, s1x, s1y, s1w, s1h), (0, 0, 255, s2x, s2y, s2w, s2h)]:
            self.draw_rect (draw, cx, cy, w, h, colour = (fr, fg, fb, 127))
        for (fr, fg, fb, cx, cy, r) in [(255, 127, 0, g1x, g1y, g1r), (0, 127, 255, g2x, g2y, g2r)]:
            self.draw_circle (draw, cx, cy, r, colour = (fr, fg, fb, 127))
        out = PIL.Image.alpha_composite (base_image, roi_image)
        out.save (os.path.join (images_folder, 'Region-of-Interests.jpg'))

    def write_properties (self, images_folder):
        w, h, d = self.imgdata.shape
        s1x, s1y, s1w, s1h, s2x, s2y, s2w, s2h, g1x, g1y, g1r, g2x, g2y, g2r = self._get_roi_properties ()
        data = {
            'start_1_center_x' : s1x,
            'start_1_center_y' : h - s2y - 1,
            'start_1_width' : s1w,
            'start_1_height' : s1h,
            'start_2_center_x' : s1x,
            'start_2_center_y' : h - s2y - 1,
            'start_2_width' : s1w,
            'start_2_height' : s1h,
            'goal_1_center_x' : g1x,
            'goal_1_center_y' : h - g1y - 1,
            'goal_1_radius' : g1r,
            'goal_2_center_x' : g2x,
            'goal_2_center_y' : h - g2y - 1,
            'goal_2_radius' : g2r
            }
        with open (os.path.join (images_folder, "roi.properties"), 'w') as fp:
            yaml.dump (data, fp, default_flow_style = False)
            fp.close ()


STRING_2_CLASS = {
    'CircularArena' : CircularArenaROIPicker,
    'TwoCircularArenas' : TwoCircularArenasROIPicker,
    'Corridor2Start2GoalROIPicker' : Corridor2Start2GoalROIPicker,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser ()
    parser.add_argument (
        '-b',
        '--background',
        type = str,
        required = True,
        help = "background image to load" )
    parser.add_argument (
        '-t',
        '--type',
        type = str,
        required = True,
        choices = STRING_2_CLASS.keys (),
        help = 'what ROI picker to use'
        )
    args = parser.parse_args()
    app = QtGui.QApplication (sys.argv)
    window = STRING_2_CLASS [args.type] (args.background)
    window.show ()
    app.exec_ ()
    print ('Region-of-interest properties: ', window._get_roi_properties ())
    window.create_mask_images ('.')
    window.create_region_of_interests_image ('.')
