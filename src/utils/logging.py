"""Centralised logging setup for the application."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]


class FFLogger:
    """Centralised logging class for the application."""

    _configured: bool = False

    @classmethod
    def get_logger(
        cls,
        name: str | None = None,
        log_dir: str | None = None,
        log_file: str | None = None,
        log_level: str | None = None,
    ) -> logging.Logger:
        """Configure centralised logging with file and stream handlers.

        Args:
            name: Name of the logger.
            log_dir: Directory for log files, relative to the project root
                unless absolute.
            log_file: Path to the log file.
            log_level: Logging level (e.g., DEBUG, INFO).

        Returns:
            Configured logger instance.
        """
        if not cls._configured:
            # A relative value (LOG_DIR=logs in .env) is resolved against the
            # project root; an absolute one is honoured as given
            log_root = Path(log_dir or os.getenv("LOG_DIR") or "logs")
            if not log_root.is_absolute():
                log_root = PROJECT_ROOT / log_root
            log_root.mkdir(parents=True, exist_ok=True)

            log_file = log_file or os.getenv("LOG_FILE") or "app.log"
            log_path = log_root / log_file

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

            cls._configured = True

        return logging.getLogger(name)
