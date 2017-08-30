
from __future__ import print_function

import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageOps
from PIL import Image
from PIL.ImageChops import difference
from PIL.ImageFilter import GaussianBlur

def function (fatigue_gain, fatigue_noise_threshold, fatigue_video_number_frames):
        w = 600
        h = 600
        prev = None
        movement = 0
        first_run = True
        for ith_frame in xrange (1, fatigue_video_number_frames + 1):
            frame_filename = 'tmp/fatigue_%04d.png' % (ith_frame)
            if prev == None:
                prev = Image.open(frame_filename)
            else:
                current = Image.open(frame_filename)

                diff = difference(current, prev)
                blur = diff.filter(GaussianBlur(radius=3))
                hist = blur.histogram()
                frame_movement = sum(hist[noise_threshold:256])/float(sum(hist))

                
                newImage = PIL.Image.new ('L', (w, h), 'white')
                pixels_prev = prev.load ()
                pixels_curr = current.load ()
                pixels_newi = newImage.load ()
                counter = 0
                for pixel1, pixel2 in zip (prev.getdata (), current.getdata ()):
                    if pixels_prev [x,y][0] > pixels_curr [x,y][0] - fatigue_gain and pixels_prev [x,y][0] < pixels_curr [x,y][0] + fatigue_gain:
                for x in xrange (w):
                    for y in xrange (h):
                        if pixels_prev [x,y][0] > pixels_curr [x,y][0] - fatigue_gain and pixels_prev [x,y][0] < pixels_curr [x,y][0] + fatigue_gain:
                            PIL.ImageDraw.Draw (newImage).rectangle (((x, y), (x + 1, y + 1)), fill = 0)
                        else:
                            counter += 1

                if first_run:
                    prev.show ()
                    current.show ()
                    newImage.show()
                    print (sum(hist[noise_threshold:256]), '  /  ', float(sum(hist)))
                    print ('gain = ', fatigue_gain, '  counter = ', counter)
                    raw_input ('Press INPUT')
                    first_run = False

                frame_movement = sum(hist[fatigue_noise_threshold:256])/float(sum(hist))
                movement += frame_movement
                print (frame_movement, ' ', end = '')

                prev = current
        movement = movement / (fatigue_video_number_frames - 1)


function (
    fatigue_gain = 20,
    fatigue_noise_threshold = 10,
    fatigue_video_number_frames = 30)
