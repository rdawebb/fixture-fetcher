"""Centralised logging setup for the application."""

import logging
import os
from logging.handlers import RotatingFileHandler

from config import LOG_FILE, LOG_LEVEL


def setup_logging() -> None:
    """Configure centralised logging with file and stream handlers.
    
    Environment variables:
        LOG_LEVEL: Logging level (default: INFO)
        LOG_FILE: Path to log file (default: app.log)
    """
    log_level = LOG_LEVEL
    log_file = LOG_FILE

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        handlers=[file_handler, stream_handler]
    )

# Initialise logging on import
setup_logging()