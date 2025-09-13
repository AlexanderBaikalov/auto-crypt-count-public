import subprocess
import logging
import os
from pathlib import Path
import time
from natsort import natsorted
import shutil
import sys
import importlib

import src.parameters
from src.logger import time_since

# Check that nnUNetv2 is indeed installed, ModuleNotFoundError otherwise
if not importlib.util.find_spec("nnunetv2"):
    raise ModuleNotFoundError("Moduel nnunetv2 was not found.")

logger = logging.getLogger(__name__)

ENV_VARS = src.parameters.ENV_VARS
NNUNET_DATASET = src.parameters.NNUNET_DATASET


def run_predictions(slice_images_dirpath):
    """Runs predictions on images in slice_images_dirpath."""
    # First delete any files starting with '.' in slice_images_dirpath
    hidden_files = natsorted(slice_images_dirpath.glob(".*"))
    if hidden_files:
        logger.warning(
            f"Detected hidden files or directories in Slice Images directory. Deleting them before proceeding with predictions: {[x.name for x in hidden_files]}"
        )
        for fp in hidden_files:
            if fp.is_file():
                fp.unlink()
            elif fp.is_dir():
                shutil.rmtree(fp)
    # Then warn the user of any non-png files
    non_png_files = [
        x for x in natsorted(slice_images_dirpath.iterdir()) if x.suffix != ".png"
    ]
    if non_png_files:
        logger.warning(
            f"Detected non-png files in Slice Images directory: {[x.name for x in non_png_files]}"
        )
    # Finally run the predict command
    segmentations_dirpath = Path(slice_images_dirpath).parent / "Slice Segmentations"
    cmd = f'nnUNetv2_predict -i "{slice_images_dirpath}" -o "{segmentations_dirpath}" -d {NNUNET_DATASET} -c 2d'
    run_command(cmd, env_vars=ENV_VARS)


def run_command(command, env_vars=None):
    """Runs given command."""
    start_time = time.time()
    logger.info(f"Running command: {command}")
    env = os.environ.copy()  # Use the current environment
    if env_vars:
        env.update(env_vars)  # Add new environment variables
    process = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=sys.stderr, text=True, env=env
    )
    # Log stdout
    if process.stdout:
        logger.info(f"Logging STDOUT from command...")
        for line in process.stdout.strip().split("\n"):
            logger.info(line)
        logger.info(f"Finished logging STDOUT from command.")
    # Check if there was an error
    return_code = process.returncode
    if return_code == 0:
        logger.info(f"Command completed successfully in {time_since(start_time)}")
    else:
        logger.error(f"Error running command. Failed with return code {return_code}.")
