import os

from PIL import Image
from PIL.ImageChops import difference
from PIL.ImageFilter import GaussianBlur

import pylab as pl
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

def evaluate_fatigue(frame_folder, noise_threshold=10):
    prev = None
    first_run = False

    movement = []

    for frame in os.listdir(frame_folder):
        if prev == None:
            prev = Image.open(os.path.join(frame_folder,frame))
        else:
            current = Image.open(os.path.join(frame_folder,frame))

            diff = difference(current, prev)
            blur = diff.filter(GaussianBlur(radius=3))
            hist = blur.histogram()

            if first_run:
                prev.show()
                current.show()
                diff.show()
                blur.show()
                first_run = False

            frame_movement = sum(hist[noise_threshold:256])/float(sum(hist))
            movement.append(frame_movement)

            prev = current

    # Show movement plot
    fig, ax = plt.subplots(1, 1)
    f, axarr = plt.subplots(2, gridspec_kw = {'height_ratios':[4, 1]})
    plt.ion()
    plt.show()

    for i, frame_file in enumerate(os.listdir(frame_folder)):

        fig.clf()

        frame = mpimg.imread(os.path.join(frame_folder,frame_file))

        x = range(len(os.listdir(frame_folder))-1)
        y = movement

        axarr[0].imshow(frame)
        axarr[1].plot(x, y, 'k-', lw=2)
        axarr[1].plot(x[i], y[i], 'or')

        pl.pause(.01)

    print(movement)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Are the bees tired?.')
    parser.add_argument('folder', metavar='FOLDER', type=str,
                        help='Video folder')

    args = parser.parse_args()
    evaluate_fatigue(args.folder)