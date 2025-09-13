import sys

VERSION = 4.0  # auto-crypt-count version number
MAC_OS = True if sys.platform == "darwin" else False  # OS (for image canvas)
LOG_FP = r"C:\Users\Public\AutoCryptCount\log.log"  # or something like 'Path(__file__).parent.parent.resolve() / "log.log"' for testing

# svs.py
THUMBNAIL_DOWNSAMPLE = 16  # assume fixed downsample factor for thumbnail image

# wsi.py
TISSUE_INTENSITY_THRESHOLD = 230
SIZE_RANGE_UM2 = (1e6, 3e6)  # lower and upper area limits for GI slice in microns^2
FORCE_OBJECTIVE = 20.0  # force the objective (resolution) of output images to this
NORM_HNE = True  # normalize the color of the output images to H&E
GRID_PATTERN = "staircase"  # or "3x3"
SAVE_RESOLUTION = "full"  # or "thumbnail" for testing

# predict.py
NNUNET_DATASET = 505
ENV_VARS = {
    "nnUNet_raw": r"C:\Users\Public\AutoCryptCount\nnUNet_raw",
    "nnUNet_preprocessed": r"C:\Users\Public\AutoCryptCount\nnUNet_preprocessed",
    "nnUNet_results": r"C:\Users\Public\AutoCryptCount\nnUNet_results",
}

# crypt_contour.py
MIN_CRYPT_SIZE = 2000  # area in pixels
DEFECT_THRESHOLD = 10  # length in pixels

# image_canvas.py
CANVAS_COLOR = "black"
TOOLBAR_COLOR = "#e3d6b8"
CRYPT_COLOR = "#89FC00"
FIRST_CRYPT_COLOR = "#00ffc1"
PROBLEM_CRYPT_COLOR = (255, 0, 0, 128)
PROBLEM_COORD_RADIUS = 100
