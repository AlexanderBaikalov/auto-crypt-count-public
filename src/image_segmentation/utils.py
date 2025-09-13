import numpy as np
import cv2
from matplotlib import pyplot as plt


def crop_label(labeled_img, label, return_binary_mask=True, return_bbox=False, pad=0):
    """Returns the cropped label from labeled_img. If return_binary_mask=True,
    returns the binary mask of just the cropped blob. Otherwise, returns the
    blob as it is in labeled_img. Returns the bounding box indices if toggled.
    Crops with given padding if given.
    """
    blob = (labeled_img == label).astype(np.uint8)
    # Get dimensions of bounding box
    contours, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bbox = cv2.boundingRect(contours[0])  # bbox = x, y, width, height
    if pad:
        x, y, width, height = bbox
        bbox = x - pad, y - pad, width + 2 * pad, height + 2 * pad
    # Crop it
    if return_binary_mask:
        cropped_blob = blob[bbox[1] : bbox[1] + bbox[3], bbox[0] : bbox[0] + bbox[2]]
    else:
        cropped_blob = labeled_img[
            bbox[1] : bbox[1] + bbox[3], bbox[0] : bbox[0] + bbox[2]
        ]
    if return_bbox:
        return cropped_blob, bbox
    else:
        return cropped_blob


def labelmap(blob_mask, return_sizes=False, connectivity=4):
    """Returns a labelmap with given connectivity of given binary mask. If
    desired, returns the sizes of all labels including bkgd (always 0th label).
    """
    if return_sizes:
        _, labeled_mask, stats, _ = cv2.connectedComponentsWithStats(
            blob_mask.astype(np.uint8), connectivity=4
        )
        return labeled_mask, stats[:, 4]
    else:
        return cv2.connectedComponents(blob_mask.astype(np.uint8), connectivity)[1]


def plot_labelmap(labelmap, ax=None, title="", axes_off=True):
    """Plots the given np.uint8 labelmap."""
    if not ax:
        fig, ax = plt.subplots(dpi=300)
    ax.imshow(labelmap)
    if title:
        ax.set_title(str(title))
    ax.axis("off" if axes_off else "on")
    return ax
