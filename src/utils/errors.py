"""List of custom exceptions for API and application errors."""

import logging
from typing import Any, Optional

## API Errors


class APIError(Exception):
    """
    Base class for API errors.
    Attributes:
        status_code: HTTP status code returned by the API.
        response: The full HTTP response object.
    """

    LOG_LEVEL = "error"

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        response: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response

    def _log(self) -> None:
        logger = logging.getLogger(__name__)
        log_func = getattr(logger, self.LOG_LEVEL)
        log_func(f"{self.__class__.__name__}: {self} (status_code: {self.status_code})")

    def handle(self) -> None:
        self._log()


class NotFoundError(APIError):
    """Raised when a requested resource is not found."""

    LOG_LEVEL = "warning"


class ValidationError(APIError):
    """Raised when a request validation fails."""

    LOG_LEVEL = "warning"


class RateLimitError(APIError):
    """Raised when the API rate limit is exceeded."""

    LOG_LEVEL = "warning"


class AuthenticationError(APIError):
    """Raised when authentication with the API fails."""

    LOG_LEVEL = "error"


class ConnectionError(APIError):
    """Raised when a network error occurs."""

    LOG_LEVEL = "warning"


class TimeoutError(APIError):
    """Raised when a request to the API times out."""

    LOG_LEVEL = "warning"


class ServerError(APIError):
    """Raised when the API server returns an error."""

    LOG_LEVEL = "error"


class ParsingError(APIError):
    """Raised when there is an error parsing the API response."""

    LOG_LEVEL = "error"


class ServiceUnavailableError(APIError):
    """Raised when the API service is unavailable."""

    LOG_LEVEL = "error"


class UnknownAPIError(APIError):
    """Raised for unknown API errors."""

    LOG_LEVEL = "error"


## Application Errors


class ApplicationError(Exception):
    """
    Base class for application errors.

    Attributes:
        context: Additional context about the error.
    """

    LOG_LEVEL = "error"

    def __init__(self, message: Optional[str] = None, context: Any = None) -> None:
        super().__init__(message)
        self.context = context

    def _log(self) -> None:
        logger = logging.getLogger(__name__)
        log_func = getattr(logger, self.LOG_LEVEL)
        log_func(f"{self.__class__.__name__}: {self} (context: {self.context})")

    def handle(self) -> None:
        self._log()


class CalendarError(ApplicationError):
    """Raised for calendar-related errors."""

    LOG_LEVEL = "error"


class ConfigurationError(ApplicationError):
    """Raised for configuration-related errors."""

    LOG_LEVEL = "error"


class DataProcessingError(ApplicationError):
    """Raised when there is an error processing data."""

    LOG_LEVEL = "error"


class ExternalServiceError(ApplicationError):
    """Raised when an external service integration fails."""

    LOG_LEVEL = "error"


class InvalidInputError(ApplicationError):
    """Raised when input data is invalid."""

    LOG_LEVEL = "error"


class ICSReadError(ApplicationError):
    """Raised when there is an error reading ICS files."""

    LOG_LEVEL = "error"


class ICSWriteError(ApplicationError):
    """Raised when there is an error writing ICS files."""

    LOG_LEVEL = "error"


class OperationError(ApplicationError):
    """Raised when an operation cannot be completed."""

    LOG_LEVEL = "error"


class TeamNotFoundError(ApplicationError):
    """Raised when a specified team is not found."""

    LOG_LEVEL = "warning"


class TeamsCacheError(ApplicationError):
    """Raised when there is an error with the teams cache."""

    LOG_LEVEL = "error"


class UnknownError(ApplicationError):
    """Raised for unknown errors."""

    LOG_LEVEL = "error"
