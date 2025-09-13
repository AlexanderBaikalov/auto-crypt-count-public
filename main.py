from src.parameters import LOG_FP
from src.logger import setup_logger, summarize_warnings, log_complete
from src.gui.control_gui import run_control_gui

if __name__ == "__main__":
    # Set root logger
    setup_logger(LOG_FP)
    # Run control gui
    run_control_gui()
    # Summarize warnings in log
    summarize_warnings()
    # Log complete
    log_complete()
