"""Tests for custom error classes."""

from unittest.mock import Mock, patch

import pytest

from utils.errors import (
    APIError,
    ApplicationError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    DataProcessingError,
    ExternalServiceError,
    ICSWriteError,
    InvalidInputError,
    NotFoundError,
    OperationError,
    ParsingError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
    UnknownAPIError,
    UnknownError,
)


class TestAPIErrors:
    """Tests for API error classes."""

    def test_api_error_initialization(self):
        """Test APIError initialization."""
        error = APIError("Test message", status_code=400, response="response")
        assert str(error) == "Test message"
        assert error.status_code == 400
        assert error.response == "response"

    @pytest.mark.parametrize(
        "error_class,message,status_code,log_level",
        [
            (NotFoundError, "Resource not found", 404, "warning"),
            (RateLimitError, "Rate limit exceeded", 429, "warning"),
            (AuthenticationError, "Auth failed", 401, "error"),
            (ServerError, "Server error", 500, "error"),
            (ServiceUnavailableError, "Service unavailable", 503, "error"),
            (UnknownAPIError, "Unknown error", 499, "error"),
        ],
    )
    def test_api_error_with_status_code(
        self, error_class, message, status_code, log_level
    ):
        """Test API error classes with status codes."""
        error = error_class(message, status_code=status_code)
        assert error.status_code == status_code
        assert error.LOG_LEVEL == log_level

    @pytest.mark.parametrize(
        "error_class,message,log_level",
        [
            (ConnectionError, "Connection failed", "warning"),
            (TimeoutError, "Request timeout", "warning"),
            (ParsingError, "Parse failed", "error"),
        ],
    )
    def test_api_error_without_status_code(self, error_class, message, log_level):
        """Test API error classes without status codes."""
        error = error_class(message)
        assert error.LOG_LEVEL == log_level

    @patch("utils.errors.logging.getLogger")
    def test_api_error_handle(self, mock_get_logger):
        """Test that handle method logs appropriately."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        error = NotFoundError("Not found", status_code=404)
        error.handle()

        mock_logger.warning.assert_called_once()


class TestApplicationErrors:
    """Tests for application error classes."""

    def test_application_error_initialization(self):
        """Test ApplicationError initialization."""
        error = ApplicationError("Test message", context="test context")
        assert str(error) == "Test message"
        assert error.context == "test context"

    @pytest.mark.parametrize(
        "error_class,message,log_level",
        [
            (ConfigurationError, "Config error", "error"),
            (DataProcessingError, "Processing failed", "error"),
            (ExternalServiceError, "Service failed", "error"),
            (InvalidInputError, "Invalid input", "error"),
            (OperationError, "Operation failed", "error"),
            (ICSWriteError, "Write failed", "error"),
            (UnknownError, "Unknown error", "error"),
        ],
    )
    def test_application_error_types(self, error_class, message, log_level):
        """Test application error classes and their log levels."""
        error = error_class(message)
        assert error.LOG_LEVEL == log_level

    def test_configuration_error_with_context(self):
        """Test ConfigurationError with context."""
        error = ConfigurationError("Config error", context="config")
        assert error.context == "config"
        assert error.LOG_LEVEL == "error"

    @patch("utils.errors.logging.getLogger")
    def test_application_error_handle(self, mock_get_logger):
        """Test that handle method logs appropriately."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        error = ConfigurationError("Config error", context="test")
        error.handle()

        mock_logger.error.assert_called_once()
