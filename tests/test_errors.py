"""Tests for custom error classes."""

from unittest.mock import Mock, patch

from src.utils.errors import (
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

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Resource not found", status_code=404)
        assert error.status_code == 404
        assert error.LOG_LEVEL == "warning"

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Rate limit exceeded", status_code=429)
        assert error.status_code == 429
        assert error.LOG_LEVEL == "warning"

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Auth failed", status_code=401)
        assert error.status_code == 401
        assert error.LOG_LEVEL == "error"

    def test_connection_error(self):
        """Test ConnectionError."""
        error = ConnectionError("Connection failed")
        assert error.LOG_LEVEL == "warning"

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("Request timeout")
        assert error.LOG_LEVEL == "warning"

    def test_server_error(self):
        """Test ServerError."""
        error = ServerError("Server error", status_code=500)
        assert error.status_code == 500
        assert error.LOG_LEVEL == "error"

    def test_parsing_error(self):
        """Test ParsingError."""
        error = ParsingError("Parse failed")
        assert error.LOG_LEVEL == "error"

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        error = ServiceUnavailableError("Service unavailable", status_code=503)
        assert error.status_code == 503
        assert error.LOG_LEVEL == "error"

    def test_unknown_api_error(self):
        """Test UnknownAPIError."""
        error = UnknownAPIError("Unknown error", status_code=499)
        assert error.status_code == 499
        assert error.LOG_LEVEL == "error"

    @patch("src.utils.errors.logging.getLogger")
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

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config error", context="config")
        assert error.context == "config"
        assert error.LOG_LEVEL == "error"

    def test_data_processing_error(self):
        """Test DataProcessingError."""
        error = DataProcessingError("Processing failed")
        assert error.LOG_LEVEL == "error"

    def test_external_service_error(self):
        """Test ExternalServiceError."""
        error = ExternalServiceError("Service failed")
        assert error.LOG_LEVEL == "error"

    def test_invalid_input_error(self):
        """Test InvalidInputError."""
        error = InvalidInputError("Invalid input")
        assert error.LOG_LEVEL == "error"

    def test_operation_error(self):
        """Test OperationError."""
        error = OperationError("Operation failed")
        assert error.LOG_LEVEL == "error"

    def test_ics_write_error(self):
        """Test ICSWriteError."""
        error = ICSWriteError("Write failed")
        assert error.LOG_LEVEL == "error"

    def test_unknown_error(self):
        """Test UnknownError."""
        error = UnknownError("Unknown error")
        assert error.LOG_LEVEL == "error"

    @patch("src.utils.errors.logging.getLogger")
    def test_application_error_handle(self, mock_get_logger):
        """Test that handle method logs appropriately."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        error = ConfigurationError("Config error", context="test")
        error.handle()

        mock_logger.error.assert_called_once()
