"""
Configuration settings for the application.
Includes API endpoints, tokens, and logging configuration.
"""

import os
from src.utils.errors import ConfigurationError


# Football Data API configuration

FOOTBALL_DATA_API = os.getenv("FOOTBALL_DATA_API", "https://api.football-data.org/v2")
FOOTBALL_DATA_API_TOKEN = os.getenv("FOOTBALL_DATA_API_TOKEN")


# Logging configuration

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "app.log")


def validate_config() -> None:
    """
    Validate critical configuration settings.
    
    Raises:
        ConfigurationError: If any critical configuration is missing or invalid.
    """
    if not FOOTBALL_DATA_API_TOKEN:
        raise ConfigurationError(
            "FOOTBALL_DATA_API_TOKEN environment variable is not set",
            context="FOOTBALL_DATA_API_TOKEN"
        )
    
    if LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        raise ConfigurationError(
            f"Invalid LOG_LEVEL: {LOG_LEVEL}. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL",
            context="LOG_LEVEL"
        )