"""Centralised error handling for the application."""

from utils.errors import APIError, ApplicationError, ConfigurationError
from utils.logging import get_logger

logger = get_logger(__name__)


def handle_error(error: Exception) -> int:
    """Handle errors by logging them and returning an exit code.

    Args:
        error: The exception to handle.

    Returns:
        Exit code: 0 for success, 1 for API/Application errors, 2 for unexpected errors.
    """
    if isinstance(error, ConfigurationError):
        error.handle()
        logger.critical("Configuration error - exiting application")
        return 1
    elif isinstance(error, (APIError, ApplicationError)):
        error.handle()
        return 1
    else:
        logger.exception("Unhandled exception")
        return 2
