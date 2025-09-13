from pathlib import Path
from PIL import Image
import numpy as np

from src.image_segmentation.norm_HnE import norm_HnE

INPUT_ERROR_MSG = "EITHER input a filepath to .png, or a PIL image and its filename"


class PNG:

    def __init__(self, filepath=None, img=None, filename=None):
        """Either a filepath must be specififed or a PIL img given with an
        associated filename.
        """
        # Retrieve the image as PIL object and its filename
        if filepath:
            self.filename = Path(filepath).stem
            self.img = Image.open(filepath)
        else:
            if not img and filename:
                raise ValueError(INPUT_ERROR_MSG)
            self.filename = filename
            self.img = img
        # Make sure image is in RGB mode
        self.img = self.img.convert("RGB")
        # Get the image properties
        self.size = self.img.size

    def resize(self, factor):
        """Resizes img by given factor."""
        width, height = self.size
        new_width = int(width * factor)
        new_height = int(height * factor)
        self.img = self.img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def norm_HnE(self):
        """Normalizes colors to HnE norm"""
        img_arr = np.array(self.img)
        normed_img_arr = norm_HnE(img_arr)[0]
        self.img = Image.fromarray(normed_img_arr, mode="RGB")

    def save(self, fp):
        self.img.save(fp)

    def show(self):
        self.img.show()
