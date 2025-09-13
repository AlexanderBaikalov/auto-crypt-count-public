import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import logging

from src.logger import add_trial_log


logger = logging.getLogger(__name__)


def run_control_gui():
    """Function to be imported to run the Control GUI."""
    root = tk.Tk()
    app = ControlGUI(master=root)
    app.mainloop()


def prepare(folder_path, import_only=False):
    """Prepares trial data at folder path."""

    from src.prepare.process_trial_data import process_trial_data

    if import_only:
        return
    process_trial_data(folder_path)


def predict(folder_path, import_only=False):
    """Runs AI predictions on images in 'Slice Images' folder within folder_path."""

    from src.predict.predict import run_predictions

    if import_only:
        return
    run_predictions(folder_path / "Slice Images")


def count(folder_path, import_only=False):
    """Counts segmentations in 'Slice Segmentations' folder within folder path."""

    from src.count.crypt_count import process_segmentations, crypt_data_to_excel

    if import_only:
        return
    seg_dir = folder_path / "Slice Segmentations"
    process_segmentations(seg_dir)
    crypt_data_to_excel(seg_dir / "crypt_data.pkl", folder_path)


def run_crypt_gui(folder_path, import_only=False):
    """Opens Crypt GUI."""
    from src.gui.crypt_gui import CryptGUI

    if import_only:
        return

    root = tk.Tk()
    app = CryptGUI(master=root, open_to=folder_path)
    app.mainloop()


# Mapping functions to checkbox labels
FUNC_MAP = {
    "Prepare trial image data": prepare,
    "Run AI predictions": predict,
    "Count crypts on predictions": count,
    "Open Crypt GUI": run_crypt_gui,
}
FUNC_MAP_R = {v: k for k, v in FUNC_MAP.items()}


def enable_function(func_label):
    """Returns True if module imports for given func_label work."""
    logger.info(f"Checking import for function: {func_label}.")
    try:
        FUNC_MAP[func_label](folder_path=None, import_only=True)
        logger.info("Check successful.")
        return True
    except ModuleNotFoundError:
        logger.warning("Imports not possible. Disabling checkbox widget.")
        return False


def correct_folder_structure(folder_path, function_labels):
    """Check that the expected folder structure exists."""

    wsi_fp = Path(folder_path, "Whole Slide Images")
    thumbnail_fp = Path(wsi_fp, "Thumbnails")
    img_fp = Path(folder_path, "Slice Images")
    seg_fp = Path(folder_path, "Slice Segmentations")
    svs_files_exist = len(list(folder_path.glob("*.svs"))) > 0
    wsi_files_exist = len(list(wsi_fp.glob("*.svs"))) > 0
    img_files_exist = len(list(img_fp.glob("*.png"))) > 0
    seg_files_exist = len(list(seg_fp.glob("*.png"))) > 0
    thumbnails_exist = len(list(thumbnail_fp.glob("*.png"))) > 0
    slice_csv_data_exists = Path(thumbnail_fp / "slide_crop_data.csv")

    checks = {
        prepare: [
            svs_files_exist
            or (wsi_files_exist and thumbnails_exist and slice_csv_data_exists),
            "no .svs files found in folder. Also no thumbnails and slide_crop_data.csv files found.\n"
            + r"If you want to process .svs files from scratch, make sure to select the trial data folder containing the raw trial data. Otherwise, if you want to process using slide_crop_data.csv, ensure that it is located in Whole Slide Images\Thumbnails\ alongside the thumbnail .png images.",
        ],
        predict: [
            img_files_exist,
            "no .png files found in 'Slice Images' folder within selected folder.\nMake sure to select the trial data folder containing the 'Slice Images' folder which contains the prepared slice images.",
        ],
        count: [
            seg_files_exist,
            "no .png files found in 'Slice Segmentations' folder within selected folder.\nMake sure to select the trial data folder containing the 'Slice Segmentations' folder which contains the AI predictions.",
        ],
        run_crypt_gui: [
            img_files_exist and seg_files_exist,
            "no .png files found in 'Slice Segmentations' folder within selected folder.\nMake sure to select the trial data folder containing the 'Slice Segmentations' folder which contains the AI predictions.",
        ],
    }

    for function, (condition, error_msg) in checks.items():
        func_label = FUNC_MAP_R[function]
        if func_label in function_labels:
            error_msg = f"'{func_label}' selected, but " + error_msg
            error_msg += f"\n\nSelected folder path: '{folder_path}'."
            try:
                # If the condition fails, return the error message
                if not condition:
                    return error_msg
                # Otherwise, return False for a successful check
                return False
            except Exception:
                # If evaluating condition raised an Exception, also return err msg.
                return error_msg
    # If none of the function_names were in check, something went wrong.
    raise ValueError(f"Selected functions are incorrect: {function_labels}.")


class ControlGUI(tk.Frame):

    def __init__(self, master=None):
        """GUI to run the prepare, predict, count, or CryptGUI functions."""
        super().__init__(master)
        # GUI setup
        logger.info("Initializing Control GUI.")
        self.master.title("Auto Crypt Count - Control GUI")
        # Create checkboxes
        self.checkboxes = {}
        for func_label in FUNC_MAP:
            var = tk.BooleanVar()
            state = "normal" if enable_function(func_label) else "disabled"
            chk = tk.Checkbutton(
                self.master, text=func_label, variable=var, state=state
            )
            chk.pack(anchor="w", padx=10, pady=5)
            self.checkboxes[func_label] = var
        # Run button
        self.run_button = tk.Button(
            self.master, text="Select Folder and Run", command=self.run
        )
        self.run_button.pack(pady=10)

    def run(self):
        """Run the selected functions in order"""
        # Get selected functions
        selected = [label for label, func in self.checkboxes.items() if func.get()]
        # If no function was selected, return.
        if not selected:
            messagebox.showinfo("Alert", "Select at least one function before running.")
            return
        # Let user pick folder. Return if no folder was picked.
        folder_path = None
        folder_selection = filedialog.askdirectory()
        if folder_selection == "":
            return
        elif folder_selection:
            folder_path = Path(folder_selection)
        logger.info(f"Selected functions {selected} at folder path {folder_path}.")
        # Check for correct folder structure in selected folder.
        if error_msg := correct_folder_structure(folder_path, selected):
            logger.warning(
                f"Error with selected folder: {error_msg.replace("\n"," ")}."
            )
            messagebox.showinfo("Alert", error_msg)
            return
        # Disable the buttons so it is clear that the control GUI is no longer used.
        self.run_button["state"] = "disabled"
        self.master.destroy()
        logger.info(f"Selected folder structure check successful. Executing functions.")
        # Create a new log in the trial directory
        add_trial_log(folder_path / "log.log")
        # Finally, run the functions.
        for func_label in selected:
            logger.info(f"Running function: '{func_label}'.")
            try:
                FUNC_MAP[func_label](folder_path)
            except Exception:
                logger.exception(f"Error running function '{func_label}'.")
                break
