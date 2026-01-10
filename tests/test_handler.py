"""Tests for the error handler module."""

from unittest.mock import Mock, patch

import pytest

from utils.errors import (
    ApplicationError,
    AuthenticationError,
    ConfigurationError,
)
from utils.handler import handle_error


class TestHandleError:
    """Tests for the handle_error function."""

    @pytest.mark.parametrize(
        "error_class,error_kwargs,expected_exit_code",
        [
            (ConfigurationError, {"message": "Test config error"}, 1),
            (
                AuthenticationError,
                {
                    "message": "Test auth error",
                    "response": Mock(),
                },
                1,
            ),
            (ApplicationError, {"message": "Test app error"}, 1),
        ],
    )
    def test_handle_custom_errors(self, error_class, error_kwargs, expected_exit_code):
        """Test handling custom errors returns exit code 1 and calls handle()."""
        error = error_class(**error_kwargs)
        with patch.object(error, "handle") as mock_handle:
            result = handle_error(error)
            assert result == expected_exit_code
            mock_handle.assert_called_once()

    @pytest.mark.parametrize(
        "error_class,error_message",
        [
            (ValueError, "Test unknown error"),
            (Exception, "Generic error"),
        ],
    )
    def test_handle_generic_exceptions(self, error_class, error_message):
        """Test handling generic exceptions returns exit code 2."""
        error = error_class(error_message)
        result = handle_error(error)
        assert result == 2

    def test_handle_configuration_error_logging(self):
        """Test that ConfigurationError is logged at critical level."""
        error = ConfigurationError("Test config error")
        with patch("utils.handler.logger") as mock_logger:
            with patch.object(error, "handle"):
                handle_error(error)
                mock_logger.critical.assert_called_once()

    def test_handle_unknown_exception_logging(self):
        """Test that unknown exceptions are logged."""
        error = RuntimeError("Test runtime error")
        with patch("utils.handler.logger") as mock_logger:
            handle_error(error)
            mock_logger.exception.assert_called_once()
