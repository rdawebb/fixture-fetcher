"""Tests for configuration module."""

from unittest.mock import patch

import pytest

from backend.config import get_config, validate_config
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

    def test_get_config_includes_competitions_and_overrides_path(self):
        """Test config exposes the keys consumers read, so edits aren't ignored."""
        with patch("backend.config.FOOTBALL_DATA_API_TOKEN", "test_token"):
            config = get_config()

        assert config["FD_COMPETITIONS"] == {"PL": "Premier League"}
        assert config["TV_OVERRIDES_PATH"].endswith("tv_overrides.yaml")

    def test_get_config_competitions_is_a_copy(self):
        """Test mutating the returned registry can't corrupt module state."""
        with patch("backend.config.FOOTBALL_DATA_API_TOKEN", "test_token"):
            get_config()["FD_COMPETITIONS"]["ELC"] = "Championship"
            assert "ELC" not in get_config()["FD_COMPETITIONS"]
