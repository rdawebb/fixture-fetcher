"""Module to write football fixtures to an ICS calendar file."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.logic.calendar.builder import CalendarBuilder
from src.logic.fixtures.models import Fixture
from src.utils import ICSWriteError, get_logger

logger = get_logger(__name__)


class ICSWriter:
    """Class to write fixtures to an ICS file using CalendarBuilder."""

    def __init__(self, fixtures: Iterable[Fixture]) -> None:
        """Initialise the ICSWriter with a list of fixtures.

        Args:
            fixtures: An iterable of Fixture objects.
        """
        self.fixtures = fixtures

    def write(self, path: Path) -> Path:
        """Build calendar and write to ICS file.

        Args:
            path: The file path to save the ICS file.

        Returns:
            Path: The path to the saved ICS file.

        Raises:
            ICSWriteError: If there is an error writing the ICS file.
        """
        logger.info(f"Starting ICS file write to {path}")

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            builder = CalendarBuilder()
            calendar = builder.add_fixtures(self.fixtures).build()
            with open(path, "wb") as file_handle:
                file_handle.write(calendar.to_ical())
            logger.info(f"ICS file successfully written to {path}")

        except Exception as e:
            logger.error(f"Error writing ICS file: {e}")
            raise ICSWriteError(f"Error writing ICS file: {e}") from e

        return path
