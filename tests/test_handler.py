"""Tests for the error handler module."""

from unittest.mock import Mock, patch

from src.utils.errors import (
    ApplicationError,
    AuthenticationError,
    ConfigurationError,
)
from src.utils.handler import handle_error


class TestHandleError:
    """Tests for the handle_error function."""

    def test_handle_configuration_error(self):
        """Test handling ConfigurationError returns exit code 1."""
        error = ConfigurationError("Test config error")
        with patch.object(error, "handle") as mock_handle:
            result = handle_error(error)
            assert result == 1
            mock_handle.assert_called_once()

    def test_handle_api_error(self):
        """Test handling APIError returns exit code 1."""
        mock_response = Mock()
        error = AuthenticationError("Test auth error", response=mock_response)
        with patch.object(error, "handle") as mock_handle:
            result = handle_error(error)
            assert result == 1
            mock_handle.assert_called_once()

    def test_handle_application_error(self):
        """Test handling ApplicationError returns exit code 1."""
        error = ApplicationError("Test app error")
        with patch.object(error, "handle") as mock_handle:
            result = handle_error(error)
            assert result == 1
            mock_handle.assert_called_once()

    def test_handle_unknown_exception(self):
        """Test handling unknown exception returns exit code 2."""
        error = ValueError("Test unknown error")
        result = handle_error(error)
        assert result == 2

    def test_handle_generic_exception(self):
        """Test handling generic Exception returns exit code 2."""
        error = Exception("Generic error")
        result = handle_error(error)
        assert result == 2

    def test_handle_configuration_error_logging(self):
        """Test that ConfigurationError is logged at critical level."""
        error = ConfigurationError("Test config error")
        with patch("src.utils.handler.logger") as mock_logger:
            with patch.object(error, "handle"):
                handle_error(error)
                mock_logger.critical.assert_called_once()

    def test_handle_unknown_exception_logging(self):
        """Test that unknown exceptions are logged."""
        error = RuntimeError("Test runtime error")
        with patch("src.utils.handler.logger") as mock_logger:
            handle_error(error)
            mock_logger.exception.assert_called_once()
