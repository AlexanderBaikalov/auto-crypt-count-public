import numpy as np
from pathlib import Path
from PIL import ImageDraw, ImageFont
import logging

import src.parameters
from src.image_segmentation.svs import SVS
from src.image_segmentation.png import PNG
from src.image_segmentation.utils import crop_label, labelmap

logger = logging.getLogger(__name__)

TISSUE_INTENSITY_THRESHOLD = src.parameters.TISSUE_INTENSITY_THRESHOLD
SIZE_RANGE_UM2 = src.parameters.SIZE_RANGE_UM2
SIZE_RANGE_ERR_MSG = "Some slices are outside expected size range - check thumbnails"
FORCE_OBJECTIVE = src.parameters.FORCE_OBJECTIVE
NORM_HNE = src.parameters.NORM_HNE
GRID_PATTERN = src.parameters.GRID_PATTERN
SAVE_RESOLUTION = src.parameters.SAVE_RESOLUTION


class WSI(SVS):
    """Subclass of SVS with added functionality for manipulating whole-slide images of
    9 GI slices.
    """

    @property
    def tissue_mask(self):
        """Returns the binary thresholded mask (np.array) of the slide tissue."""
        if not hasattr(self, "_tissue_mask"):
            # Get binary mask of thumbnail below threshold
            arr = np.array(self.thumbnail.convert("L"), dtype=np.uint8)
            self._tissue_mask = arr < TISSUE_INTENSITY_THRESHOLD
        return self._tissue_mask

    def get_GI_slice_data(self):
        """Returns the locations and sizes of the 9 GI slices in the slide."""
        # Label each blob
        labeled_blobs, sizes = labelmap(self.tissue_mask, return_sizes=True)
        # Get the 9 largest blob labels excluding background
        slice_labels = np.argsort(sizes)[-10:-1]
        # Convert their sizes to square micrometers
        sizes = sizes[slice_labels] * (self.thumbnail_downsample * self.mpp) ** 2
        # Warn if the these 9 sizes are outside the expected range
        if not all((sizes > SIZE_RANGE_UM2[0]) & (sizes < SIZE_RANGE_UM2[1])):
            logger.warning(SIZE_RANGE_ERR_MSG + f" of {self.filename}.svs.")
        # Get slice data for each slice
        slice_data = {}
        for slice_label, size in zip(slice_labels, sizes):
            _, bbox = crop_label(labeled_blobs, slice_label, return_bbox=True)
            x, y, width, height = bbox
            mean_coord = [y + height / 2, x + width / 2]  # (y, x)
            slice_data[slice_label] = {"bbox": bbox, "center": mean_coord}
        return slice_data

    def order_GI_slice_data(self, slice_data, grid_pattern="staircase"):
        """Adds order attribute to the slice data by grid position, staircase or 3x3"""
        # Prepare group indices depending on grid pattern
        if grid_pattern == "3x3":
            group_indices = [(0, 3), (3, 6), (6, 9)]
        elif grid_pattern == "staircase":
            group_indices = [(0, 2), (2, 5), (5, 9)]
        # Sort slice data by y position (list of tuples now)
        slice_data_y = sorted(slice_data.items(), key=lambda x: x[1]["center"][0])
        # Loop through the groups, assigning order indices based on x position
        ordered_slice_labels = []
        for i, j in group_indices:
            group = slice_data_y[i:j]
            slice_data_x = dict(sorted(group, key=lambda x: x[1]["center"][1]))
            ordered_slice_labels.extend(slice_data_x.keys())
        # Add the order attribute (starts at 1 ends at 9) to the slice data
        for i, slice_label in enumerate(ordered_slice_labels):
            slice_data[slice_label]["order"] = i + 1
        # Sort the slice data by order
        slice_data = dict(sorted(slice_data.items(), key=lambda x: x[1]["order"]))
        return slice_data

    def draw_GI_slice_boxes(self, slice_data, output_fp):
        """Draws the bounding boxes of the 9 GI slices on the thumbnail and saves it."""
        # Draw the bounding boxes on a copy of the thumbnail
        draw_thumbnail = self.thumbnail.copy()
        draw = ImageDraw.Draw(draw_thumbnail)
        for data in slice_data.values():
            x, y, width, height = data["bbox"]
            left, right = x - (0.02 * width), x + (1.02 * width)
            upper, lower = y - (0.02 * height), y + (1.02 * height)
            draw.rectangle([(left, upper), (right, lower)], outline="red", width=3)
            draw.text(
                (x + width / 2, y - 50),
                str(data["order"]),
                fill="red",
                font=ImageFont.load_default(30),
            )
        # Save the drawn thumbnail image
        draw_thumbnail.save(output_fp)

    def save_GI_slices(self, slice_data, output_dir, append=None):
        """Saves the cropped image of each of the 9 slices from slice_data in either
        'full' or 'thumbnail' (faster) resolution as desired. Appends 'append' to
        filename when saving.
        """
        # Loop through the slices, cropping and saving each with a 2% margin
        for data in slice_data.values():
            logger.debug(f"Saving slice {data['order']}: {self.filename}")
            x, y, width, height = data["bbox"]
            left, right = x - (0.02 * width), x + (1.02 * width)
            upper, lower = y - (0.02 * height), y + (1.02 * height)
            box = (left, upper, right, lower)
            # Use the thumbnail if desired
            if SAVE_RESOLUTION == "thumbnail":
                slice_img = self.thumbnail.crop(box)
            # Otherwise convert thumbnail coords to full resolution coords
            elif SAVE_RESOLUTION == "full":
                left, upper, right, lower = (
                    int(self.thumbnail_downsample * x) for x in box
                )
                # Now get the sub_image in full res from the original image
                sub_img_dimensions = (right - left, lower - upper)
                slice_img = self.extract((left, upper), sub_img_dimensions)
            # Get the PNG object of the img, using the order number in the filename
            png = PNG(img=slice_img, filename=f"{self.filename}_0{data['order']}")
            # Resize the image if desired
            if FORCE_OBJECTIVE and not FORCE_OBJECTIVE == self.objective:
                logger.warning(
                    f"{png.filename} resolution mismatch, forcing objective."
                )
                png.resize(factor=FORCE_OBJECTIVE / self.objective)
            # Color norm the image if desired
            if NORM_HNE:
                png.norm_HnE()
            # Save the image with append to filename
            append = append if append else ""
            png.save(Path(output_dir, png.filename + f"{append}.png"))
