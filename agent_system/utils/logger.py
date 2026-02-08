import logging
import os
import sys
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).parent.parent.parent

# Log directory
LOG_DIR = BASE_DIR / "log"
LOG_FILE = LOG_DIR / "agent.log"

def setup_logger():
    """Sets up the centralized logger."""
    if not LOG_DIR.exists():
        os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("agent_system")
    logger.setLevel(logging.INFO)

    # Prevent logs from propagating to the root logger if it has already been configured elsewhere
    logger.propagate = False

    # Clear existing handlers to avoid duplicates if re-initialized
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    
    return logger

# Singleton-like instance
logger = setup_logger()

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)
