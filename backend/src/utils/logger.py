"""
Logging Configuration

Centralized logging setup for the application.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(name: str = "video_platform", level: int = logging.INFO) -> logging.Logger:
    """
    Setup and configure logger

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Optional: File handler for production
    # Uncomment to enable file logging
    # log_dir = Path("logs")
    # log_dir.mkdir(exist_ok=True)
    # log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    #
    # file_handler = logging.FileHandler(log_file)
    # file_handler.setLevel(logging.DEBUG)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    return logger


# Create default logger
logger = setup_logger()
