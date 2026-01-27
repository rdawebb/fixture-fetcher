"""Centralised logging setup for the application."""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def get_logger(
    name: Optional[str] = None,
    log_dir: Optional[str] = None,
    log_file: Optional[str] = None,
    log_level: Optional[str] = None,
) -> logging.Logger:
    """Configure centralised logging with file and stream handlers.

    Args:
        name: Name of the logger.
        log_dir: Directory for log files.
        log_file: Path to the log file.
        log_level: Logging level (e.g., DEBUG, INFO).

    Returns:
        Configured logger instance.
    """
    if not getattr(get_logger, "_configured", False):
        log_dir = log_dir or os.getenv("LOG_DIR") or "logs"
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        log_file = log_file or os.getenv("LOG_FILE") or "app.log"
        log_path = Path(log_dir) / log_file

        log_level = (log_level or os.getenv("LOG_LEVEL") or "INFO").upper()

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

        get_logger._configured = True  # type: ignore[attr-defined]

    return logging.getLogger(name)
