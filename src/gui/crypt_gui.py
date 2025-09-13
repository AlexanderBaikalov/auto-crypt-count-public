import numpy as np
import tkinter as tk
from tkinter.filedialog import askopenfilename
import pickle
import time
import pandas as pd
import ast
from pathlib import Path
from natsort import natsorted
import logging
import random

import src.parameters
from src.count.excel import Excel
from src.count.crypt_count import get_crypt_data
from src.gui.image_canvas import ImageCanvas

logger = logging.getLogger(__name__)

VERSION = src.parameters.VERSION
TOOLBAR_COLOR = src.parameters.TOOLBAR_COLOR


def loading(func):
    """Decorator function to get the window in 'Loading' state.
    Note that if any changes are made to the states of this widgets during the
    decorated function call, those changes will be lost! Only to be used for
    class methods, since 'self' must be the first argument.
    """

    def wrapper(*args, **kwargs):
        # Get 'self'
        GUI = args[0]
        # Add loading to the filename.
        GUI.filename_str.set(f"Loading {GUI.filename}...")
        # Get copy of toggleable widgets' states and disable them
        toggleable_widgets, og_states = (
            GUI.toggleable_widgets.keys(),
            GUI.toggleable_widgets.values(),
        )
        for widget in toggleable_widgets:
            widget["state"] = "disabled"
        # Refresh screen so changes appear
        GUI.master.update()
        # Run function
        func(*args, **kwargs)
        # Return filename
        GUI.filename_str.set(GUI.filename)
        # Return all widgets to their original states before func().
        for widget, state in zip(GUI.toggleable_widgets, og_states):
            widget["state"] = state
        # Refresh screen so changes appear
        GUI.master.update()

    return wrapper


class CryptGUI(tk.Frame):

    def __init__(self, master=None, open_to=None):
        """CryptGUI Frame contains a toolbar and ImageCanvas."""
        super().__init__(master)
        logger.info("Initializing Crypt GUI.")
        self.hover_crypt_label = None
        self.problem_crypts = []
        self.latest_outline_width = 8
        self.outline_width = 0
        self.saved_files = []
        self.upload_counter = 0
        self.current_upload_error = False
        self.pil_image = None
        self.open_to = open_to
        self.master.title(f"Crypt GUI v{VERSION}")
        self.create_toolbar()
        self.image_canvas = ImageCanvas(self)
        self.create_infobar()

    def create_toolbar(self):
        """Creates a toolbar on the top of the GUI frame with all buttons
        disabled except for the Browse button.
        """
        toolbar = tk.Frame(self.master, bd=1, relief=tk.SUNKEN, bg=TOOLBAR_COLOR)
        # Counter Frame
        counter_frame = tk.LabelFrame(toolbar)
        counter_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(counter_frame, text="Counter").pack(side=tk.TOP)
        self.counter_str = tk.StringVar()
        self.counter_entry = tk.Entry(
            counter_frame, textvariable=self.counter_str, width=10
        )
        self.counter_entry.pack(side=tk.LEFT)
        fname_frame = tk.LabelFrame(toolbar)
        # Browse button
        self.browse_btn = tk.Button(
            toolbar,
            text="Browse",
            command=self.browse,
            borderwidth=0,
            highlightthickness=0,
            bd=4,
        )
        self.browse_btn.pack(side=tk.LEFT, padx=20)
        # Randomize checkbutton
        self.randomize = tk.IntVar()  # Variable to hold the check button state
        self.randomize_btn = tk.Checkbutton(
            toolbar,
            text="Randomize",
            variable=self.randomize,
            command=lambda: logger.info(
                f"Toggled 'Randomize' to {self.randomize.get()}."
            ),
        )
        self.randomize_btn.pack(side=tk.LEFT, padx=20)
        # Filename Frame with scroll buttons and filename
        fname_frame = tk.LabelFrame(toolbar)
        fname_frame.pack(side=tk.LEFT, padx=10)
        self.filename_str = tk.StringVar(
            value="Write counter name.\nThen " + "Browse to select file."
        )
        self.fname_label = tk.Label(
            fname_frame, justify=tk.CENTER, textvariable=self.filename_str
        )
        self.fname_label.pack(side=tk.TOP)
        self.scroll_left_btn = tk.Button(
            fname_frame, text="<<", command=lambda: self.scroll(-1)
        )
        self.scroll_left_btn.pack(side=tk.LEFT)
        self.scroll_right_btn = tk.Button(
            fname_frame, text=">>", command=lambda: self.scroll(+1)
        )
        self.scroll_right_btn.pack(side=tk.LEFT)
        # Model Count Frame
        mc_frame = tk.LabelFrame(toolbar)
        mc_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(mc_frame, text="Model Count").pack(side=tk.TOP)
        self.model_count = tk.IntVar()
        tk.Label(mc_frame, textvariable=self.model_count).pack(side=tk.BOTTOM)
        # True Count Frame
        tc_frame = tk.LabelFrame(toolbar)
        tc_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(tc_frame, text="True Count").pack(side=tk.TOP)
        self.tc_minus_btn = tk.Button(
            tc_frame, text="-", command=lambda: self.update_true_count(-1)
        )
        self.tc_minus_btn.pack(side=tk.LEFT)
        self.true_count = tk.IntVar()
        self.true_count_entry = tk.Entry(
            tc_frame, textvariable=self.true_count, width=3
        )
        self.true_count_entry.pack(side=tk.LEFT)
        self.tc_plus_btn = tk.Button(
            tc_frame, text="+", command=lambda: self.update_true_count(+1)
        )
        self.tc_plus_btn.pack(side=tk.LEFT)
        # Create Save button
        self.save_btn = tk.Button(
            toolbar,
            text="Save",
            command=self.save,
            borderwidth=0,
            highlightthickness=0,
            bd=4,
        )
        self.save_btn.pack(side=tk.LEFT, padx=10)
        # Notes Frame
        note_frame = tk.LabelFrame(toolbar)
        note_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(note_frame, text="Note:").pack(side=tk.LEFT)
        self.note = tk.StringVar(value="")
        note_entry = tk.Entry(note_frame, textvariable=self.note, width=30)
        note_entry.pack(side=tk.RIGHT)
        # Discard button
        discard_cmd = lambda: self.note.set("DISCARD: " + self.note.get())
        self.discard_btn = tk.Button(
            toolbar,
            text="Discard",
            command=discard_cmd,
            borderwidth=0,
            highlightthickness=0,
            bd=4,
        )
        self.discard_btn.pack(side=tk.LEFT, padx=10)
        # Outlines frame
        outline_frame = tk.LabelFrame(toolbar)
        outline_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(outline_frame, text="Outlines").pack(side=tk.TOP)
        self.outline_minus_btn = tk.Button(
            outline_frame, text="-", command=lambda: self.update_outlines(-1)
        )
        self.outline_minus_btn.pack(side=tk.LEFT)
        self.outline_btn = tk.Button(
            outline_frame, text="On", command=lambda: self.update_outlines(0)
        )
        self.outline_btn.pack(side=tk.LEFT)
        self.outline_plus_btn = tk.Button(
            outline_frame, text="+", command=lambda: self.update_outlines(+1)
        )
        self.outline_plus_btn.pack(side=tk.LEFT)
        # Review checkbutton
        self.review_mode = tk.IntVar()  # Variable to hold the check button state
        self.review_btn = tk.Checkbutton(
            toolbar,
            text="Review",
            variable=self.review_mode,
            command=self.set_review_mode,
        )
        self.review_btn.pack(side=tk.LEFT, padx=20)
        # Place toolbar and set it as attribute
        toolbar.pack(side=tk.TOP, fill=tk.X, ipadx=10, ipady=10)
        self.toolbar = toolbar
        # Toggle everything off except for Browse button and Counter entry
        for widget in self.toggleable_widgets:
            widget["state"] = "disabled"
        self.counter_entry["state"] = "normal"
        self.browse_btn["state"] = "normal"

    def create_infobar(self):
        """Creates an info bar at the bottom of the GUI frame with the current
        mouse coordinates and any hovered label.
        """
        infobar = tk.Frame(self.master, bd=1, relief=tk.SUNKEN)
        coord_label = tk.Label(
            infobar, textvariable=self.image_canvas.hover_coords_display, padx=10
        )
        coord_label.pack(side=tk.LEFT, padx=10)
        crypt_label = tk.Label(
            infobar, textvariable=self.image_canvas.hover_crypt_display, padx=10
        )
        crypt_label.pack(side=tk.RIGHT, padx=10)
        # Place toolbar and set it as attribute
        infobar.pack(side=tk.BOTTOM, fill=tk.X, ipadx=10, ipady=1)
        self.infobar = infobar

    @property
    def filename(self):
        """Returns filename of current filepath, _0000 and .png from suffix."""
        return self.filepath.stem.replace("_0000", "")

    @property
    def directory(self):
        """Returns directory path of current filepath. Defaults to 'open_to'
        directory if no filepath exists yet.
        """
        if hasattr(self, "filepath"):
            return Path(self.filepath).parent
        else:
            return self.open_to

    @property
    def seg_dir(self):
        """Returns the filepath to the corresponding Segmentations folder of
        the currently selected folder of Png files.
        """
        return self.directory.parent / "Slice Segmentations"

    @property
    def seg_filepath(self):
        """Returns the filepath to the corresponding .png segmentation of the
        current slice image.
        """
        return self.seg_dir / (self.filename + ".png")

    @property
    def pkl_path(self):
        """Returns the filepath to the crypt_data.pkl file in seg_dir."""
        return self.seg_dir / "crypt_data.pkl"

    @property
    def filenames_in_dir(self):
        """Returns filename stems of all .png files in current directory sorted
        alphanumerically and randomized if toggled.
        """
        # Get filenames of all .png files in current directory sorted alphanumerically
        filenames_in_dir = [
            x.stem.replace("_0000", "") for x in natsorted(self.directory.glob("*.png"))
        ]
        # If self.randomize, randomize the files and prepenbd already-saved files
        if self.randomize.get():
            random.seed(2)  # fixed random seed for filename sorting
            random.shuffle(filenames_in_dir)
            unsaved = [x for x in filenames_in_dir if x not in self.saved_files]
            filenames_in_dir = self.saved_files + unsaved
        return filenames_in_dir

    @property
    def toggleable_widgets(self):
        """Returns dictionary of all Button and Entry widgets within
        LabelFrames, along with their current states.
        """

        def toggleable(widget):
            tog_widgs = [tk.Button, tk.Entry, tk.Checkbutton]
            if any([isinstance(widget, x) for x in tog_widgs]):
                return True
            return False

        def is_LabelFrame(widget):
            if isinstance(widget, tk.LabelFrame):
                return True
            return False

        toggleable_widgets = {}
        for widget in self.toolbar.winfo_children():
            if toggleable(widget):
                toggleable_widgets[widget] = widget["state"]
            elif is_LabelFrame(widget):
                for sub_widget in widget.winfo_children():
                    if toggleable(sub_widget):
                        toggleable_widgets[sub_widget] = sub_widget["state"]
        return toggleable_widgets

    def browse(self, filepath=None):
        """Allows the user to browse for a .png image. Loads it."""
        # First check that the counter has been set
        if self.counter_str.get() == "":
            return
        else:
            self.counter = self.counter_str.get()
            self.counter_entry["state"] = "disabled"
        if not filepath:
            filepath = askopenfilename(
                filetypes=[("PNG file", "*.png")], initialdir=self.directory
            )
        # Handle if no filepath was selected while browsing
        if filepath == "":
            return
        old_dir = self.directory
        # Set current filepath
        self.filepath = Path(filepath)
        # Reset color of fname box to default
        self.fname_label.configure(bg=self.master.cget("bg"))
        # If directory changed, preload crypts and check for file mismatches.
        if old_dir != self.directory:
            self.check_file_mismatches()
            # Preload crypt data if not already done.
            self.preload_crypt_data()
        # Try loading data of current slice.
        try:
            # Reset any saved variables that should be reset upon new image
            self.note.set("")
            self.current_upload_error = False
            self.hover_crypt_label = None
            self.problem_crypts = []
            # Upload
            self.upload()
        # If error occurs, notify user and return.
        except Exception:
            logger.exception(f"Error uploading {self.filepath}.")
            self.upload_Error()
            return
        # If current filename has already been saved, make the fn box orange
        #  and add 'RECOUNT: ' to note. Don't do this in Review mode.
        if self.filename in self.saved_files and not self.review_mode.get():
            # if all filenames in dir are in self.saved_files, green and notify
            if all([x in self.saved_files for x in self.filenames_in_dir]):
                self.fname_label.configure(bg="green")
                self.filename_str.set(self.filename_str.get() + "\n(All files saved!)")
            else:
                self.fname_label.configure(bg="orange")
                self.filename_str.set(self.filename_str.get() + "\n(Already saved)")
            self.note.set("RECOUNT: " + self.note.get())
        # Enable all toggleable widgets if this is the first loaded image or if
        # the last loaded image produced an upload_Error. Except counter entry.
        if self.upload_counter == 1 or self.current_upload_error:
            for widget in self.toggleable_widgets:
                widget["state"] = "normal"
            self.counter_entry["state"] = "disabled"
        if self.outline_width == 0:
            self.outline_minus_btn["state"] = "disabled"
            self.outline_plus_btn["state"] = "disabled"
        # Enable the 'save' button every time a new image is uploaded.
        self.save_btn["state"] = "normal"
        # Start the clock for this file's timer
        self.timer = time.time()
        # If review mode is on, set it appropriately
        if self.review_mode.get():
            self.set_review_mode(change=False)

    def check_file_mismatches(self):
        """Checks that the filenames in both Slice Images and Segmentations directories
        match up. Logs warning if not.
        """
        pngs = [
            fp.name.replace("_0000", "")
            for fp in natsorted(self.directory.glob("*.png"))
        ]
        segs = [fp.name for fp in natsorted(self.seg_dir.glob("*.png"))]
        diffs = [x for x in pngs if x not in segs]
        if diffs:
            logger.warning(
                f"The following files were found in Slice Images but NOT in Slice Segmentations: {diffs}"
            )

    @loading
    def upload(self):
        """Loads segmentation of current filepath and displays it on canvas."""
        self.upload_seg()
        self.upload_counter += 1
        # Update the 'Model Count' and 'True Count' with current # of crypts.
        num_crypts = len(self.crypt_data["contours"])
        self.model_count.set(num_crypts)
        self.true_count.set(num_crypts)
        # Display the image on the canvas.
        self.image_canvas.display_image(self.filepath)
        # Update outlines, if any
        if num_crypts > 0:
            self.image_canvas.draw_outlines()

    def upload_Error(self):
        # Disable all toggleable widgets except browse and scroll buttons.
        for widget in self.toggleable_widgets:
            widget["state"] = "disabled"
        for btn in [self.browse_btn, self.scroll_left_btn, self.scroll_right_btn]:
            btn["state"] = "normal"
        # Notify of error in filename box
        self.filename_str.set(
            f"\nError loading {self.filename}.\nTry a " + "different file."
        )
        self.fname_label.configure(bg="red")
        # Update the current upload error value
        self.current_upload_error = True

    def set_review_mode(self, change=True):
        """Toggles on or off review mode."""

        def extract_data(data):
            """Extract the true count, difference, problem crypts, and note
            from data, a row from the crypt_counts.xlsx dataframe.
            """
            tc = data["True Count"]
            diff = data["Difference"]
            pc = data["Problem Crypts"]
            note = data["Note"]
            # tc and diff could be np.nan or a float
            tc = int(tc) if not np.isnan(tc) else "n/a"
            diff = int(diff) if not np.isnan(diff) else "n/a"
            # pc could be np.nan or a str of a list of ints and tuples
            pc = ast.literal_eval(pc) if type(pc) == str else []
            # note could be str or np.nan
            note = "" if type(note) == float and np.isnan(note) else str(note)
            return tc, diff, pc, note

        # Toggle off the randomize button
        self.randomize.set(False)
        # Define widgets to change
        widgets = (
            self.tc_plus_btn,
            self.tc_minus_btn,
            self.save_btn,
            self.discard_btn,
            self.true_count_entry,
        )
        # Change the review mode if desired
        if change:
            # If it's being turned off, re-enable widgets
            if not self.review_mode.get():
                for widget in widgets:
                    widget["state"] = "normal"
            # Rebrowse to current image to reset everything
            self.browse(self.filepath)
        # Otherwise, this is a new browse so disable buttons and display values
        else:
            # If turning on, turn the widgets off
            if self.review_mode.get():
                for widget in widgets:
                    widget["state"] = "disabled"
            excel_fp = self.directory.parent / "crypt_counts.xlsx"
            # Load the data, but warn if this user does not yet have a sheet
            try:
                df = pd.read_excel(excel_fp, sheet_name=self.counter)
            except ValueError:
                self.fname_label.configure(bg="orange")
                self.filename_str.set(
                    self.filename_str.get()
                    + "\n(Counter has no saved data - can't review)"
                )
                return
            # If the current file has not yet been saved to the excel, warn
            if self.filename not in df["Filename"].values:
                self.fname_label.configure(bg="orange")
                self.filename_str.set(
                    self.filename_str.get()
                    + "\n(File has no saved data - can't review)"
                )
                return
            # Get the last instance of this filename's entry
            data = df[df["Filename"] == self.filename]
            data = data.loc[data.index[-1]]
            tc, diff, pc, note = extract_data(data)
            # Set the tc, prob_crypts, and note to the values in the Excel
            self.true_count.set(tc)
            self.problem_crypts = pc
            self.note.set(note)
            # Check that the difference is as expected based on problem_crypts
            coords = [x for x in pc if type(x) == tuple]
            labels = [x for x in pc if type(x) != tuple]
            if diff != "n/a" and diff != len(coords) - len(labels):
                self.fname_label.configure(bg="orange")
                self.filename_str.set(
                    self.filename_str.get()
                    + "\n(Difference doesn't match marked problem crypts)"
                )
            # Refresh display with new outlines
            self.image_canvas.draw_outlines()

    def scroll(self, direction):
        """Browses for the next file of current filename in given
        alphanumerically sorted direction. If self.randomize, browses instead through
        randomized list with already-saved files prepended to the list.
        """
        filenames_in_dir = self.filenames_in_dir
        # Find the index of the current file
        i = filenames_in_dir.index(self.filename)
        # Increase/decrease i based on direction of scroll
        i += direction
        # Handle scrolls from the last to the first item of the list.
        if i >= len(filenames_in_dir):
            i = len(filenames_in_dir) - i
        # Define new filepath and browse to it
        new_filepath = self.directory / (filenames_in_dir[i] + ".png")
        # Append '_0000' to filepath stem if it doesn't exist
        if not new_filepath.exists():
            new_filepath = Path(str(new_filepath).replace(".png", "_0000.png"))
        self.browse(filepath=new_filepath)

    def update_true_count(self, val):
        """Updates the true count value by adding val."""
        self.true_count.set(self.true_count.get() + val)

    def save(self):
        """Saves the current crypt counts to the excel file."""
        logger.info(
            f"Saving slice data of current slice in GUI ({self.filename}) to Excel."
        )
        # Create excel in parent dir of the dir of the currently loaded file.
        if not hasattr(self, "excel"):
            self.excel = Excel(self.directory.parent, self.counter)
        # Get data
        mc = self.model_count.get()
        tc = self.true_count.get()
        diff = tc - mc
        time_spent = int(time.time() - self.timer)
        note = self.note.get()
        if self.problem_crypts:
            prob_labels = [x for x in self.problem_crypts if type(x) != tuple]
            prob_coords = [x for x in self.problem_crypts if type(x) == tuple]
            problems = str(sorted(prob_labels) + prob_coords)
        else:
            problems = ""
        if "DISCARD" in note:
            mc = tc = diff = "n/a"
        data = {
            "Filename": self.filename,
            "Model Count": mc,
            "True Count": tc,
            "Difference": diff,
            "Time [s]": time_spent,
            "Problem Crypts": problems,
            "Note": note,
        }
        # Save data to excel
        self.excel.append(data)
        # Add current filename to saved files.
        self.saved_files.append(self.filename)
        # Disable Save button until next file is loaded
        self.save_btn["state"] = "disabled"

    def upload_seg(self):
        """Gets the segmentation data from current filepath."""
        # First try loading from pkl
        try:
            with open(self.pkl_path, "rb") as file:
                self.crypt_data = pickle.load(file)[self.filename]
                # If the loaded crypt data was an error message, raise error
                if type(self.crypt_data) == str:
                    raise ValueError(
                        "Loaded crypt_data was an error message: {self.crypt_data}"
                    )
        # If that doesn't work, load directly from segmentation file.
        except Exception:
            logger.exception(
                f"Could not load {self.filename} from crypt_data.pkl file. Loading directly from Slice Segmentations instead."
            )
            self.crypt_data = get_crypt_data(self.seg_filepath)

    def update_outlines(self, val):
        """Updates thickness of outlines or toggles them on/off (val=0)."""
        if val != 0:
            self.outline_width += 2 * val
            # width cannot be <1
            if self.outline_width < 1:
                self.outline_width = 1
        # If passed val is 0, toggle outlines on/off
        elif val == 0:
            # If outlines were toggled on, toggle off, erase, and change btn
            if self.outline_width:
                # save the last value
                self.latest_outline_width = self.outline_width
                self.outline_width = 0
                self.outline_minus_btn["state"] = "disabled"
                self.outline_plus_btn["state"] = "disabled"
                self.outline_btn["text"] = "On"
            # If outlines were toggled off, toggle on, draw, and change btn
            else:
                self.outline_width = self.latest_outline_width
                self.outline_minus_btn["state"] = "normal"
                self.outline_plus_btn["state"] = "normal"
                self.outline_btn["text"] = "Off"
        # Refresh display with new outlines
        self.image_canvas.draw_outlines()

    def preload_crypt_data(self):
        """Preloads data into crypt_data.pkl if it doesn't already exist. Also
        adds all this data to Excel file.
        """
        # If crypt_data.pkl already exists, exit.
        if self.pkl_path.exists():
            return
        all_crypt_data = {}
        # Go through all segmentations
        filenames = [x for x in natsorted(self.seg_dir.glob("*.png"))]
        length = len(filenames)
        for i, fn in enumerate(filenames):
            # Display which file is being preloaded in the filename box.
            self.filename_str.set(f"Preloading {fn.stem} ({i + 1}/{length})...")
            self.master.update()
            # Save crypt data to all_crypt_data
            try:
                crypt_data = get_crypt_data(self.seg_dir / fn)
            except Exception as e:
                # If error occurs, save crypt_data as that error.
                logger.exception(f"Error encountered while preloading {fn}.")
                crypt_data = str(e)
            all_crypt_data[fn.stem] = crypt_data
        # Save dictionary as crypt_data.pkl
        with open(self.pkl_path, "wb") as file:
            pickle.dump(all_crypt_data, file, protocol=-1)
        # Reset filename display
        self.filename_str.set(f"{self.filename}")
        # Save all the pickled crypt data into Excel file
        # Create excel in parent dir of the dir of the currently loaded file.
        try:
            if not hasattr(self, "excel"):
                # Create a new sheet with name Pre-Load (counter)
                self.excel = Excel(self.directory.parent, f"Pre-Load ({self.counter})")
            logger.info(f"Saving preloaded crypt data to {self.excel.filepath}.")
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
                self.excel.append(data)
            # Now delete self.excel so data gets saved to a new sheet
            del self.excel
            logger.info(f"Successfuly saved Excel file.")
        except Exception:
            logger.exception("Error saving preloaded crypt data to crypt_counts.xlsx")
