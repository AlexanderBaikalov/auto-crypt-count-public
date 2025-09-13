import logging
import time
from pathlib import Path

import src.parameters

# logger.py
LOGGING_KWARGS = {
    "level": logging.DEBUG,
    "format": "%(asctime)s|%(levelname)s|%(name)s| %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
}


def setup_logger(log_fp):
    """Set up centralized logging configuration."""
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(LOGGING_KWARGS["level"])

    # Create formatter
    formatter = logging.Formatter(
        LOGGING_KWARGS["format"], datefmt=LOGGING_KWARGS["datefmt"]
    )

    # Public File handler (INFO and above)
    file_handler = logging.FileHandler(log_fp)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Capture handler (for warnings and errors)
    capture_handler = logging.Handler()
    capture_handler.records = []  # Store records in a list

    def emit(record):
        """Capture only WARNING and ERROR logs."""
        if record.levelno >= logging.WARNING:
            capture_handler.records.append(formatter.format(record))

    capture_handler.emit = emit
    capture_handler.setLevel(logging.WARNING)

    # Add handlers to the logger (avoid duplicates)
    if not logger.hasHandlers():
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(capture_handler)

    # Store capture handler as a logger attribute for later access
    logger.capture_handler = capture_handler
    # Log that new logger was started
    new_log(logger, log_fp)


def add_trial_log(trial_log_fp):
    """Add a trial log file handler to the existing logger."""
    logger = logging.getLogger()

    # Create formatter (reuse existing format)
    formatter = logging.Formatter(
        LOGGING_KWARGS["format"], datefmt=LOGGING_KWARGS["datefmt"]
    )
    # File handler (Private log file, INFO and above)
    private_file_handler = logging.FileHandler(trial_log_fp)
    private_file_handler.setLevel(logging.INFO)
    private_file_handler.setFormatter(formatter)

    # Add the new handler
    logger.addHandler(private_file_handler)

    # Log the addition of the private log file
    new_log(logger, trial_log_fp)

    return logger


def new_log(logger, log_fp):
    # Log that new logger was started
    logger.info("-------------------- NEW LOG --------------------")
    logger.info(f"Welcome to auto-crypt-count!")
    logger.info(f"Log instantiated from user {get_user()} at {log_fp}")
    # Log all params in parameters.py
    logger.info(f"Parameters module loaded with parameter values:")
    for name in dir(src.parameters):
        if name.isupper():  # Only log constants (uppercase variables)
            value = getattr(src.parameters, name)
            logging.info(f"     {name} = {value}")


def summarize_warnings():
    """Print all captured warnings and errors at the end."""
    logger = logging.getLogger()
    # Access the capture handler from the logger
    capture_handler = getattr(logger, "capture_handler", None)
    if capture_handler.records:
        records = "\n".join(capture_handler.records)
        logger.warning(f"##########################################")
        logger.warning(f"###   Summary of Warnings and Errors   ###")
        logger.warning(f"##########################################\n{records}")
    else:
        logger.info(f"Summary of Warnings and Errors: none occured.")


def log_complete():
    """Log that everything is complete."""
    logger = logging.getLogger()
    logger.info("End of task. Logging complete.")


def time_since(event_time):
    """Returns a string of the formatted time in seconds since the given time."""
    seconds = time.time() - event_time
    if seconds < 1:
        return "<1 s"
    else:
        return f"{round(seconds)} s"


def get_user():
    """Returns the name of the user if possible."""
    parts = Path.home().parts
    if "Users" in parts:
        try:
            return parts[parts.index("Users") + 1]
        except Exception:
            return "(no username found)"
    else:
        return "(no username found)"
