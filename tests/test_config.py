"""Tests for configuration module."""

from unittest.mock import patch

import pytest

from backend.config import validate_config
from utils.errors import ConfigurationError


class TestConfig:
    """Tests for configuration validation."""

    def test_validate_config_success(self):
        """Test that validate_config passes with valid config."""
        with patch("backend.config.FOOTBALL_DATA_API_TOKEN", "test_token"):
            validate_config()

    def test_validate_config_missing_token(self):
        """Test that validate_config fails without API token."""
        with patch("backend.config.FOOTBALL_DATA_API_TOKEN", ""):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_config()

            assert "FOOTBALL_DATA_API_TOKEN" in str(exc_info.value)
