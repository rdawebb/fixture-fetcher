"""
Configuration settings for the application.
Includes API endpoints, tokens, paths, and logging configuration.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.utils.errors import ConfigurationError

load_dotenv(Path(__file__).parent.parent.parent / ".env")


# Football Data API configuration

FOOTBALL_DATA_API = os.getenv("FOOTBALL_DATA_API", "https://api.football-data.org/v4/")
FOOTBALL_DATA_API_TOKEN = os.getenv("FOOTBALL_DATA_API_TOKEN")

# Cache configuration

CACHE_PATH = Path(os.getenv("CACHE_PATH", "data/cache/teams.yaml"))
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Logging configuration

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")
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
            context="FOOTBALL_DATA_API_TOKEN",
        )

    if LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        raise ConfigurationError(
            f"Invalid LOG_LEVEL: {LOG_LEVEL}. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL",
            context="LOG_LEVEL",
        )


def get_config() -> dict:
    """
    Get the current configuration settings.

    Returns:
        dict: A dictionary of configuration settings.
    """
    return {
        "FOOTBALL_DATA_API": FOOTBALL_DATA_API,
        "FOOTBALL_DATA_API_TOKEN": FOOTBALL_DATA_API_TOKEN,
        "CACHE_PATH": str(CACHE_PATH),
        "LOG_LEVEL": LOG_LEVEL,
        "LOG_DIR": LOG_DIR,
        "LOG_FILE": LOG_FILE,
    }
