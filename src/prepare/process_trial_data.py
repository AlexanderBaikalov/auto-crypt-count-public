from pathlib import Path
import shutil
from natsort import natsorted
import csv
import logging
import time

from src.logger import time_since
from src.prepare.wsi import WSI

logger = logging.getLogger(__name__)


def process_trial_data(trial_data_dir):
    """Given a directory containing all WSI (.svs files), creates and populates the
    following folder structure:
    - wsi_data_dir
        - Whole Slide Images
            - Thumbnails
        - Slice Images
        - Slice Segmentations
    """
    trial_start = time.time()
    logger.info(f"Processing trial data in {trial_data_dir}")
    # Define directory and file paths
    trial_data_dir = Path(trial_data_dir)  # ensure is Path object
    wsi_dir = Path(trial_data_dir, "Whole Slide Images")
    thumbnail_dir = Path(wsi_dir, "Thumbnails")
    slice_dir = Path(trial_data_dir, "Slice Images")
    csv_fp = Path(thumbnail_dir, "slide_crop_data.csv")
    # Check if retrieving slice_data_from_csv
    slice_data_from_csv = csv_fp.exists()
    # If computing slice data from scratch, create the necessary directories
    if not slice_data_from_csv:
        logger.info("Processing slice data from scratch.")
        # Create the WSI directory and move files in
        wsi_dir.mkdir()
        for fp in trial_data_dir.glob("*.svs"):
            shutil.move(fp, Path(wsi_dir, fp.name))
        # Create the Thumbnails and Slice Images directories
        thumbnail_dir.mkdir()
        slice_dir.mkdir()
    else:
        logger.info(
            f"Loading slice data from CSV file at {csv_fp}. If any WSI file processing fails, ensure that slice data CSV file is correct or delete it entirely to load from scratch instead."
        )
    # Process each WSI file
    wsi_fps = natsorted(wsi_dir.glob("*.svs"))
    for i, fp in enumerate(wsi_fps):
        logger.info(f"Processing WSI file {i + 1}/{len(wsi_fps)}: {fp.name}")
        try:
            wsi_start = time.time()
            # Create the WSI object
            w = WSI(fp)
            # Get slice data (either from csv or from the WSI)
            if slice_data_from_csv:
                slice_data = get_slice_data_from_csv(w.filename, csv_fp)
            else:
                slice_data = w.get_GI_slice_data()
                slice_data = w.order_GI_slice_data(slice_data)
                save_to_csv(slice_data, w.filename, csv_fp)
            # Save thumbnails with slice boxes drawn
            w.draw_GI_slice_boxes(slice_data, Path(thumbnail_dir, w.filename + ".png"))
            # Save the slice images, appending '_0000' to filenames for nnUNet
            w.save_GI_slices(slice_data, slice_dir, append="_0000")
            logger.info(f"Finished processing WSI file in {time_since(trial_start)}.")
        except Exception:
            logger.exception(f"Error processing {fp.name}. Skipping and moving on.")
    logger.info(f"Finished processing trial data in {time_since(wsi_start)}.")


def save_to_csv(slice_data, wsi_filename, fp):
    """Saves the slice_data from WSI of given filename to the .csv file at fp."""
    # Prepare csv data
    csv_data = []
    for data in slice_data.values():
        x, y, width, height = data["bbox"]
        csv_data.append(
            {
                "WSI": wsi_filename,
                "Slice": data["order"],
                "Top Left x": x,
                "Top Left y": y,
                "Bottom Right x": x + width,
                "Bottom Right y": y + height,
            }
        )
    # Write the dictionary to the CSV file
    mode = "w" if not Path(fp).exists() else "a"
    with open(fp, mode=mode, newline="") as file:
        writer = csv.DictWriter(file, fieldnames=csv_data[0].keys())
        if mode == "w":
            writer.writeheader()  # Write header (column names) if file is empty
        writer.writerows(csv_data)  # Write the rows from the dictionary


def get_slice_data_from_csv(wsi_filename, fp):
    """Returns the slice data from the CSV file at fp for the given WSI filename."""
    # Read the CSV into a list of dictionaries
    with open(fp, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
    # Filter the data for the given WSI filename
    data = [row for row in data if row["WSI"] == wsi_filename]
    # Convert the data to the slice_data format (dict of dicts) and return
    slice_data = {}
    for row in data:
        order, x, y, x2, y2 = [int(x) for x in list(row.values())[1:]]
        slice_data[f"{order} (from csv)"] = {
            "order": order,
            "bbox": (x, y, x2 - x, y2 - y),
        }
    return slice_data
