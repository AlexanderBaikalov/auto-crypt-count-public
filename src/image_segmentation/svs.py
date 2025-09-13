import slideio
from pathlib import Path
from PIL import Image
import logging

import src.parameters

logger = logging.getLogger(__name__)

THUMBNAIL_DOWNSAMPLE = src.parameters.THUMBNAIL_DOWNSAMPLE


class SVS:
    """Manipulate SVS image files using slideio."""

    def __init__(self, filepath):
        # Get the filename and slide/scene objects
        self.filename = Path(filepath).stem
        self.slide = slideio.open_slide(str(filepath), "SVS")
        self.scene = self.slide.get_scene(0)
        # Get the image resolution (meters per pixel)
        x_res, y_res = self.scene.resolution
        if x_res != y_res:
            raise ValueError("Different x and y resolutions.")
        self.mpp = x_res * 1e6  # Convert meters per pixel to microns per pixel
        # Get the objective power and dimensions
        self.objective = float(self.scene.magnification)  # lens objective power (zoom)
        self.levels = [0]  # slideio doesn't expose level details directly
        self.dimensions = self.scene.rect[2:]  # scene rect gives (x, y, width, height)
        # Get the thumbnail image
        self.thumbnail = Image.fromarray(
            self.scene.read_block(
                size=(
                    self.dimensions[0] // THUMBNAIL_DOWNSAMPLE,
                    self.dimensions[1] // THUMBNAIL_DOWNSAMPLE,
                )
            )
        )  # PIL Image object
        self.thumbnail_downsample = THUMBNAIL_DOWNSAMPLE
        logger.debug(f"New SVS file: {self.info}.")

    @property
    def info(self):
        """Returns a string of information about the svs file."""
        info = (
            f"{self.filename}.svs INFO: Image res: {round(float(self.mpp), 3)} um/pixel"
            f" | Image dimensions: {self.dimensions} pixels"
            f" | Objective power: {self.objective}"
            f" | Thumbnail downsample: {THUMBNAIL_DOWNSAMPLE}"
        )
        return info

    def extract(self, top_left_pixel, dimensions, show=False):
        """Returns an extracted image with the given parameters from level 0.
        Top left pixel should be in the level 0 coordinate frame.
        """
        rect = (
            top_left_pixel[0],
            top_left_pixel[1],
            dimensions[0],
            dimensions[1],
        )
        region = Image.fromarray(self.scene.read_block(rect))
        if show:
            Image.fromarray(region).show()
        return region
