"""Tests for configuration module."""

from unittest.mock import patch

import pytest

from src.config import validate_config
from src.utils.errors import ConfigurationError


class TestConfig:
    """Tests for configuration validation."""

    def test_validate_config_success(self):
        """Test that validate_config passes with valid config."""
        with patch("src.config.FOOTBALL_DATA_API_TOKEN", "test_token"), patch(
            "src.config.LOG_LEVEL", "INFO"
        ):
            validate_config()

    def test_validate_config_missing_token(self):
        """Test that validate_config fails without API token."""
        with patch("src.config.FOOTBALL_DATA_API_TOKEN", ""):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_config()

            assert "FOOTBALL_DATA_API_TOKEN" in str(exc_info.value)

    def test_validate_config_invalid_log_level(self):
        """Test that validate_config fails with invalid log level."""
        with patch("src.config.FOOTBALL_DATA_API_TOKEN", "test_token"), patch(
            "src.config.LOG_LEVEL", "INVALID"
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_config()

            assert "LOG_LEVEL" in str(exc_info.value)

    def test_validate_config_all_valid_log_levels(self):
        """Test that all valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            with patch("src.config.FOOTBALL_DATA_API_TOKEN", "test_token"), patch(
                "src.config.LOG_LEVEL", level
            ):
                # Should not raise
                validate_config()
