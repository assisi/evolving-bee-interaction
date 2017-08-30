import os

import pylab as pl
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

import numpy as np

from scipy.ndimage import gaussian_filter
from skimage import io
from skimage.color.colorconv import rgb2grey
from skimage.feature.blob import blob_dog
from skimage.morphology import reconstruction, erosion, dilation
from skimage.morphology.grey import opening
from skimage.morphology.selem import diamond
from skimage.util.dtype import img_as_float
from skimage.feature import blob_doh


def evaluate_fatigue(frame_folder, background_folder, noise_threshold_upper=0.6, noise_threshold_lower=0.2):
    prev = None
    first_run = True

    movement = []

    bg_frame = os.listdir(background_folder)[0]
    background = img_as_float(rgb2grey(io.imread(os.path.join(background_folder,bg_frame))))



    for frame in os.listdir(frame_folder):

        # Convert to float: Important for subtraction later which won't work with uint8
        foreground = img_as_float(rgb2grey(io.imread(os.path.join(frame_folder,frame))))
        image = np.abs(foreground - background)

        #image = gaussian_filter(image, 1)

        seed = np.copy(image)
        seed[1:-1, 1:-1] = image.min()
        mask = image

        dilated = reconstruction(seed, mask, method='dilation')

        clean = image - dilated
        clean[clean < noise_threshold_lower] = 0.0
        clean[clean > noise_threshold_upper] = 0.0
        clean = opening(clean)

        # Blob detection
        blobs_doh = blob_dog(clean*255, min_sigma=10, max_sigma=30, threshold=0.1, overlap=0.99)

        if first_run:
            fig, (ax0, ax1, ax2) = plt.subplots(nrows=1,
                                                ncols=3,
                                                figsize=(15, 8),
                                                sharex=True,
                                                sharey=True)

            ax0.imshow(image, cmap='gray')
            ax0.set_title('difference image')
            ax0.axis('off')
            ax0.set_adjustable('box-forced')

            ax1.imshow(clean, vmin=image.min(), vmax=image.max(), cmap='gray')
            ax1.set_title('cleaned')
            ax1.axis('off')
            ax1.set_adjustable('box-forced')

            ax2.imshow(foreground, cmap='gray')
            print('Min: %f, Max: %f' %(np.min(clean), np.max(clean)))
            ax2.set_title('blob')
            ax2.axis('off')
            ax2.set_adjustable('box-forced')
            print(blobs_doh)
            for blob in blobs_doh:
                y, x, r = blob
                c = plt.Circle((x, y), r, color='c', linewidth=2, fill=False)
                ax2.add_patch(c)

            fig.tight_layout()
            plt.show()

            first_run = False

def setup_graphing(n_frames):
    fig, (ax_vid, ax_plot) = plt.subplots(nrows=2,
                                        ncols=1,
                                        figsize=(15, 8),
                                        sharex=True)

    ax_plot.xlim = [0,n_frames]

    return fig, ax_vid, ax_plot

def graph_loop(frame, dispersion, blobs, i_frames, n_frames, fig, ax_vid, ax_plot):
    fig.clf()

    x = range(n_frames)
    y = dispersion

    ax_vid.imshow(frame)
    for blob in blobs:
        y, x, r = blob
        c = plt.Circle((x, y), r, color='c', linewidth=2, fill=False)
        ax_vid.add_patch(c)
    ax_plot.plot(x, y, 'k-', lw=2)
    ax_plot.plot(x[i_frames], y[i_frames], 'or')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Are the bees tired?.')
    parser.add_argument('folder', metavar='FOLDER', type=str,
                        help='Video folder')
    parser.add_argument('background', metavar='BACKGROUND', type=str,
                        help='Background folder')

    args = parser.parse_args()
    evaluate_fatigue(args.folder, args.background)