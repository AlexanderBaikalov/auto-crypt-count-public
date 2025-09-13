from natsort import natsorted
from pathlib import Path
import logging
import numpy as np
from PIL import Image
import cv2
import pickle
import time

from src.count.crypt_contour import CryptContour
from src.count.excel import Excel
from src.logger import time_since

logger = logging.getLogger(__name__)


def get_crypt_data(seg_fp):
    """Given the filepath to the segmentation .png file, returns a dict,
    crypt_data, with the img size and the cv2 contours of all contiguous areas
    (crypts) larger than MIN_CRYPT_SIZE. Separates them based on convex defects.
    Returns None instead of crypt data if there are no crypts.
    """
    # Get segmentation array
    seg_arr = np.array(Image.open(seg_fp).convert("L"), dtype=np.uint8)
    # Get contours (no chain approx because we need to have all the points stored to split contours)
    unseparated_contours, _ = cv2.findContours(
        seg_arr.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )
    # Get all separated contours
    contours = []
    for c in unseparated_contours:
        crypt_contour = CryptContour(c)
        contours.extend(crypt_contour.separated_contours)
    # Now sort the contours by their y-coords so the topmost one is first
    contours = sorted(contours, key=lambda contour: contour[0][0][1])
    # Get the total average and variance size of all the crypts
    sizes = [cv2.contourArea(c) for c in contours]
    if sizes:
        size_total, size_av, size_std = (
            round(f(sizes)) for f in [np.sum, np.mean, np.std]
        )
    else:
        size_total = size_av = size_std = 0
    # Put together the crypt data
    crypt_data = {
        "shape": seg_arr.shape,
        "contours": contours,
        "size_total": size_total,
        "size_av": size_av,
        "size_std": size_std,
    }
    return crypt_data


def process_segmentations(seg_dir):
    """Loads crypt data for all segmentations in seg_dir into crypt_data.pkl"""
    all_crypt_data = {}
    start_time = time.time()
    # Go through and process each segmentation
    logger.info(f"Processing crypt data of segmentations in {seg_dir}.")
    for seg_fp in natsorted(seg_dir.glob("*.png")):
        # Save crypt data to all_crypt_data
        try:
            crypt_data = get_crypt_data(seg_fp)
        except Exception as e:
            # If error occurs, save crypt_data as that error.
            logger.exception(
                f"Error loading crypt data for {seg_fp}. Skipping and moving on."
            )
            crypt_data = str(e)
        all_crypt_data[seg_fp.stem] = crypt_data
    logger.info(f"Finished processing segmentations in {time_since(start_time)}.")
    # Save dictionary as crypt_data.pkl in seg_dir
    crypt_data_fp = Path(seg_dir, "crypt_data.pkl")
    logger.info(f"Saving crypt data to .pkl file: {crypt_data_fp}.")
    with open(crypt_data_fp, "wb") as file:
        pickle.dump(all_crypt_data, file, protocol=-1)
    logger.info("Successfuly saved crypt data to .pkl file.")


def crypt_data_to_excel(crypt_data_fp, excel_dir):
    """Save pickled crypt data at crypt_data_fp to excel file in excel_dir."""
    logger.info(f"Saving crypt data to crypt_counts.xlsx Excel file in {excel_dir}.")
    # Retrieve all_crypt_data
    with open(crypt_data_fp, "rb") as file:
        all_crypt_data = pickle.load(file)
    # Create excel
    excel = Excel(excel_dir, f"Pre-Load (Automated)")
    for fn in all_crypt_data:
        # Get data and save to Excel
        fn_crypt_data = all_crypt_data[fn]
        # Handle if crypt_data load was an error
        if type(fn_crypt_data) == str:
            mc = f"ERROR: {fn_crypt_data}"
            shape = st = sa = ss = ""
        else:
            mc = len(fn_crypt_data["contours"])
            shape = str(fn_crypt_data["shape"])
            size_params = ["size_total", "size_av", "size_std"]
            st, sa, ss = (int(fn_crypt_data[x]) for x in size_params)
        data = {
            "Filename": fn,
            "Model Count": mc,
            "Shape": shape,
            "Size Total": st,
            "Size Average": sa,
            "Size Stdev": ss,
        }
        excel.append(data)
    logger.info("Successfuly saved crypt data to Excel file.")
