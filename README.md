# auto-crypt-count

auto-crypt-count is a Python package to automate the digital image analysis of the
crypt (microcolony) assay. This package handles:
- preparation of the whole-slide digital microscope slide .SVS images into cropped .PNG images of each slice
- deep-learning based prediction of the crypt locations
- image analysis to count and record the borders of crypts
- a graphical user interface to view and edit the results (Crypt GUI)
    - NOTICE: if you are only interested in installing & running the Crypt GUI, skip below to the heading crypt-gui


## Installation

These installation steps have already been done and only need to be repeated if auto-crypt-count is to be run on a new computer.

### Step 1: Setup Public Folder
1. Open Command Prompt (cmd.exe). Create and populate the AutoCryptCount folder within the Public user directory and create a virtual environment with the required packages:
```bat
mkdir AutoCryptCount
mkdir AutoCryptCount\nnUNet_raw
mkdir AutoCryptCount\nnUNet_preprocessed
mkdir AutoCryptCount\nnUNet_results
```
2. Download the trained model 'Dataset505_CryptModelv5' and place it into 'AutoCryptCount\nnUNet_results\'.

### Step 2: Setup Python package in Public Folder
1. Download the Python Installer (3.12.8 in my case but newer versions should also be fine): https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
2. Run it as an Administrator > Customize Installation > Next > Install Python 3.12 for all users > Check all except last 2 (download ...) > install location should be C:\Program Files\Python312 > Install
3. Open Command Prompt (cmd.exe). Check that Python works by typing 
```bat
python
>>> exit()
```
4. Create a virtual environment within the AutoCryptCount folder with the required packages.
```bat
mkdir AutoCryptCount\autocryptcount_env
python -m venv AutoCryptCount\autocryptcount_env
AutoCryptCount\autocryptcount_env\Scripts\activate.bat
pip3 install torch==2.6.0 torchaudio==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126
pip3 install nnunetv2==2.6.0
pip3 install natsort==8.4.0 slideio==2.7.1 opencv-python==4.11.0.86 openpyxl==3.1.5
```
5. Edit the following line in the nnUNet source code if it is not already edited (following https://github.com/MIC-DKFZ/nnUNet/issues/2681):
AutoCryptCount\autocryptcount_env\Lib\site-packages\nnunetv2\inference\predict_from_raw_data.py
from:
```python
checkpoint = torch.load(join(model_training_output_dir, f'fold_{f}', checkpoint_name), map_location=torch.device('cpu'))
```
to:
```python
checkpoint = torch.load(join(model_training_output_dir, f'fold_{f}', checkpoint_name), map_location=torch.device('cpu'), weights_only=False)
```
6. Download auto-crypt-count and place it into 'AutoCryptCount\'.


## Running auto-crypt-count

1. Open Command Prompt (cmd.exe) and type the following commands:
```bat
AutoCryptCount\autocryptcount_env\Scripts\activate.bat
python AutoCryptCount\auto-crypt-count\main.py
```
That's it!
This option runs the main.py file in the auto-crypt-count Python package. This allows for flexibility; for instance, the entire auto-crypt-count could be replaced with an updated version and everything would still work. Alternatively, the parameters in auto-crypt-count\src\parameters.py can be changed and these changed will be reflected in the program when it is run. This option assumes that Installation Steps 1 and 2 have been completed.


## Usage
Upon opening, auto-crypt-count displays a control GUI with a few options:
1. Prepare trial image data
2. Run AI predictions
3. Count crypts on predictions
4. Open Crypt GUI

If any functions are disabled (not checkable), this indicates that the relevant python packages for those functions could not be found. Check the functions you want to execute, press 'Select Folder and Run', and navigate to the folder with the whole-slide image data (.svs files) for the trial you wish to analyze. Note that the trial data folder you select must contain the images like so (the names are irrelevant):
```markdown
Trial XYZ\
    mouse1.svs
    mouse2.svs
    mouse3.svs
    ...
```

After running, the folder will have the following structure
```markdown
Trial XYZ\
    Whole Slide Images\
        Thumbnails\
            mouse1.png
            mouse2.png
            mouse3.png
            ...
            slide_crop_data.csv
        mouse1.svs
        mouse2.svs
        mouse3.svs
        ...
    Slice Images\
        mouse1_01_0000.png
        mouse1_02_0000.png
        ...
        mouse2_01_0000.png
        mouse2_02_0000.png
        ...
    Slice Segmentations\
        mouse1_01.png
        mouse1_02.png
        ...
        mouse2_01.png
        mouse2_02.png
        ...
        crypt_data.pkl
    crypt_counts.xlsx
    log.log
```

### Descriptions of Function Execution
1. Prepare trial image data
    - Whole Slide Images
        - The .svs files are all placed in a folder called 'Whole Slide Images\'.
        - A low resolution .png image of each .svs file is placed into a folder called 'Whole Slide Images\Thumbnails\'.
        - On each .png thumbnail, the automatically-determined crop regions are shown for each of the 9 slices in order.
        - A .csv file is saved at 'Whole Slide Images\Thumbnails\slide_crop_data.csv' listing the crop box pixel coordinates for each slice on each thumbnail image.
    - Slice Images
        - A high-resolution, resolution-normalized, color-normalized image of each cropped slice is saved into a folder called 'Slice Images\'.
        - The suffix '_0000' is appended to each image's filename. Ignore this; it is important only for the nnUNet predictions in the next step.
    - If you want to change the crop regions (e.g. if the auto-crop didn't work correctly), edit the crop box pixel coordinates of each slice you want to fix in the slide_crop_data.csv file. Then, run the function 'Prepare trial image data' anew. If the program detects that slide_crop_data.csv already exists, it will use the coordinates in that .csv file to crop the slices instead of automatically determining its own.

2. Run AI predictions
    - This function runs an nnUNet command to run predictions on the images in Slice Images\.
    - The trained nnUNet model is referred to as '505', referring to the data in AutoCryptCount\nnUNet_results\Dataset505_CryptModelv5.
    - The results of the predictions, binary segmentation maps in .png format, are placed into a folder called 'Slice Segmentations'. These appear just as black rectangles and are uninteresting to look at.

3. Count crypts on predictions
    - This function goes through each segmentation file in Slice Segmentations\ and counts the number of crypts, as well as saves the borders of each crypt.
    - Results are saved in Slice Segmentations\crypt_data.pkl, in a format that is not human-readable, but is used by the Crypt GUI.
    - Results are also saved in crypt_counts.xlsx, a human-readable file with the crypt counts for all images in the tab 'Pre-Load (Automated)'. It is critical that this file remains in its location, as it will be searched for by the Crypt GUI.

4. Open Crypt GUI
    - This function opens the Crypt GUI.
    - Enter your name (counter name).
    - Browse to select the slice .png image files you want to analyze (should auto-open to the trial data folder).
    - Control crypt border outline visibility and thickness using the control panel on the top right.
    - Move and zoom the image by clicking, dragging, and scrolling on it. Dobule-click it to re-center it.
    - Use the 'True Count' panel to adjust the model crypt count to what you believe is correct.
    - Right click on any erroneous crypt to highlight it. Right click on any non-detected crypt to denote it.
    - Press 'Save' to save your edits on this image (both to True Count and to any right-click edits).
    - Saved results will go into crypt_counts.xlsx in a new tab under your name.
    - Scroll to the next image by using the left and right arrows next to the filename. Scrolling will delete the edits data from the last image if it was not saved.
    - Select 'Randomize' to randomize the order in which images appear.
    - Select 'Review' to view the edits made by the current counter on any images which have been saved to crypt_counts.xlsx.

5. Logging
    - As soon as the auto-crypt-count program is run, a log file is created at AutoCryptCount\log.log.
    - Additionally, as soon as functions have been selected to be run at a trial folder location, a new log file is created in that folder.
    - Both log files are updated with any information, warnings, and errors during function processing. 



## License

[MIT](https://choosealicense.com/licenses/mit/)