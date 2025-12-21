"""Centralised logging setup for the application."""

import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from src.backend.config import get_config


def get_logger(
    name: Optional[str] = None,
    log_dir: Optional[str] = None,
    log_file: Optional[str] = None,
    log_level: Optional[str] = None,
) -> logging.Logger:
    """Configure centralised logging with file and stream handlers.

    Args:
        name (Optional[str]): Name of the logger.
        log_dir (str, optional): Directory for log files.
        log_file (str, optional): Path to the log file.
        log_level (str, optional): Logging level (e.g., DEBUG, INFO).

    Returns:
        logging.Logger: Configured logger instance.
    """
    config = get_config()
    if not getattr(get_logger, "_configured", False):
        log_dir = log_dir or config.get("LOG_DIR") or "logs"
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        log_file = log_file or config.get("LOG_FILE") or "app.log"
        log_path = Path(log_dir) / log_file

        log_level = (log_level or config.get("LOG_LEVEL") or "INFO").upper()

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = RotatingFileHandler(
            log_path, maxBytes=1 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            handlers=[file_handler, stream_handler],
        )

        get_logger._configured = True

    return logging.getLogger(name)
