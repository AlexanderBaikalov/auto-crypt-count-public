from pathlib import Path
from PIL import Image
import shutil
import csv
import logging
import tkinter as tk

from src.logger import setup_logger, summarize_warnings

# Set root logger for tests
setup_logger(Path(__file__).parent.resolve() / "tests.log")
logger = logging.getLogger(__name__)

# Set filepaths for easy access
HOME_DIRPATH = Path(__file__).resolve().parents[1]
TEST_DATA_DIRPATH = Path(HOME_DIRPATH, "tests/data/")
SVS_FP = Path(TEST_DATA_DIRPATH, "input/wsi_example.svs")

# First ensure that output_dir exists
output_dir = Path(TEST_DATA_DIRPATH, "output")
if not output_dir.exists():
    output_dir.mkdir()


def test_png():
    from src.image_segmentation.png import PNG

    logger.info("Running test: test_png")
    p = PNG(Path(TEST_DATA_DIRPATH, "input/slice_example.png"))
    p.norm_HnE()
    p.resize(0.9)
    p.save(Path(TEST_DATA_DIRPATH, "output/png_normHnE.png"))


def test_svs():
    from src.image_segmentation.svs import SVS

    logger.info("Running test: test_svs")
    s = SVS(SVS_FP)
    OUTPUT_FP = Path(TEST_DATA_DIRPATH, "output/svs_example_thumbnail.png")
    s.thumbnail.save(OUTPUT_FP)


def test_wsi():
    from src.prepare.wsi import WSI

    logger.info("Running test: test_wsi")
    w = WSI(SVS_FP)
    OUTPUT_FP = Path(TEST_DATA_DIRPATH, "output/wsi_tissue_mask.png")
    Image.fromarray(w.tissue_mask).convert("L").save(OUTPUT_FP)
    slice_data = w.get_GI_slice_data()
    slice_data = w.order_GI_slice_data(slice_data)
    w.draw_GI_slice_boxes(
        slice_data, Path(TEST_DATA_DIRPATH, "output/wsi_slice_boxes.png")
    )
    output_png_dir = Path(TEST_DATA_DIRPATH, "output/wsi_example_pngs")
    if output_png_dir.exists():
        shutil.rmtree(output_png_dir)
    output_png_dir.mkdir()
    w.save_GI_slices(slice_data, output_png_dir)


def test_prepare():
    from src.prepare.process_trial_data import process_trial_data

    logger.info("Running test: test_prepare")
    # Empty trial_dir and add svs files to it
    trial_dir = Path(TEST_DATA_DIRPATH, "output/Test Trial")
    if trial_dir.exists():
        shutil.rmtree(trial_dir)
    trial_dir.mkdir()
    shutil.copy(SVS_FP, Path(trial_dir, SVS_FP.name))
    shutil.copy(SVS_FP, Path(trial_dir, SVS_FP.name.replace(".svs", "copy.svs")))
    # Then process all WSI in it
    process_trial_data(trial_dir)
    logger.info("Running test: test_prepare from modified csv")
    # Change values in the csv file
    csv_fp = Path(trial_dir, "Whole Slide Images/Thumbnails/slice_data.csv")
    with open(csv_fp, mode="r", newline="") as file:
        rows = list(csv.reader(file))
    # Modify the value of the Bottom Right y column of each row of wsi_example2
    for row in rows[1:]:
        if row[0] == "wsi_examplecopy":
            row[5] = int(row[5]) + 200
    # Write the modified data back to the CSV
    with open(csv_fp, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(rows)
    # Then process all WSI from the csv
    process_trial_data(trial_dir)


def test_predict():
    from src.predict.predict import run_predictions

    logger.info("Running test: test_predict")
    slice_images_dirpath = Path(TEST_DATA_DIRPATH, "output/Test Trial/Slice Images")
    if not slice_images_dirpath.exists():
        logger.warning("Running test_prepare so that input data exists.")
        test_prepare()
    run_predictions(slice_images_dirpath)


def test_cryptcontour():
    from src.count.crypt_contour import get_all_separated_contours

    logger.info("Running test: test_cryptcontour")
    seg_fp = Path(
        TEST_DATA_DIRPATH,
        "input/example_segmentations/Slice Segmentations/svsMDA01_01.png",
    )
    img_fp = seg_fp.parent.parent / "Slice Images" / Path(seg_fp.stem + "_0000.png")
    output_dir = Path(TEST_DATA_DIRPATH, "output/example_segmentations/contours")
    output_dir.mkdir(parents=True, exist_ok=True)
    get_all_separated_contours(seg_fp, img_fp, plot_all=True, output_dir=output_dir)


def test_cryptcount():
    from src.count.crypt_count import process_segmentations, crypt_data_to_excel

    logger.info("Running test: test_cryptcount")
    # Copy segmentations from input to output.
    seg_input_dir = Path(
        TEST_DATA_DIRPATH, "input/example_segmentations/Slice Segmentations/"
    )
    seg_dir = Path(
        TEST_DATA_DIRPATH, "output/example_segmentations/Slice Segmentations/"
    )
    if seg_dir.exists():
        shutil.rmtree(seg_dir)
    shutil.copytree(seg_input_dir, seg_dir)
    # Count crypts
    process_segmentations(seg_dir)
    # Save to excel
    crypt_data_to_excel(Path(seg_dir, "crypt_data.pkl"), seg_dir)


def test_cryptgui():
    from src.gui.crypt_gui import CryptGUI

    logger.info("Running test: test_cryptgui")
    # Copy example segmentations folder to output example trial.
    trial_input_dir = Path(TEST_DATA_DIRPATH, "input/example_segmentations")
    trial_dir = Path(TEST_DATA_DIRPATH, "output/example_trial")
    if trial_dir.exists():
        shutil.rmtree(trial_dir)
    shutil.copytree(trial_input_dir, trial_dir)
    # Start Crypt GUI
    root = tk.Tk()
    app = CryptGUI(master=root)
    app.mainloop()
    # Once that is finished, start another crypt gui to test multiple counters
    root = tk.Tk()
    app = CryptGUI(master=root)
    app.mainloop()
    logger.info("Crypt GUI closed.")


def test_controlgui():
    from src.gui.control_gui import ControlGUI

    logger.info("Running test: test_controlgui")
    # Copy svs file from input to output Full Trial Data
    trial_dir = Path(TEST_DATA_DIRPATH, "output/Full Trial Data")
    if trial_dir.exists():
        shutil.rmtree(trial_dir)
    trial_dir.mkdir()
    shutil.copy(SVS_FP, trial_dir / "example.svs")
    # If testing on device where predict doesn't work, uncomment the following lines
    # to copy some segmentations over for use.
    #     # shutil.copytree(
    #     Path(TEST_DATA_DIRPATH, "input/example_segmentations/Slice Segmentations"),
    #     trial_dir / "Slice Segmentations",
    # )
    # Run control GUI
    root = tk.Tk()
    app = ControlGUI(master=root)
    app.mainloop()


def run_all_tests():
    test_png()
    test_svs()
    test_wsi()
    test_prepare()
    test_predict()
    test_cryptcontour()
    test_cryptcount()
    test_cryptgui()
    test_controlgui()
    summarize_warnings()
