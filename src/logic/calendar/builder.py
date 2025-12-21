"""Module to build an iCalendar from football fixtures."""

from __future__ import annotations

from typing import Iterable

from icalendar import Calendar

from src.logic.calendar.formatter import EventFormatter
from src.logic.fixtures.models import Fixture
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CalendarBuilder:
    """Class to build a calendar from fixtures."""

    def __init__(self) -> None:
        """Initialise the CalendarBuilder."""
        self.calendar = Calendar()
        self.calendar.add("prodid", "-//Football Fixture Fetcher//mxm.dk//EN")
        self.calendar.add("version", "2.0")
        self.formatter = EventFormatter()

    def add_fixtures(self, fixtures: Iterable[Fixture]) -> CalendarBuilder:
        """Add fixtures to the calendar.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.

        Returns:
            CalendarBuilder: The current instance of CalendarBuilder.
        """
        for fixture in fixtures:
            event = self.formatter.format_event(fixture)
            self.calendar.add_component(event)
            logger.debug(
                f"Added fixture {fixture.home_team} vs {fixture.away_team} to calendar"
            )

        return self

    def build(self) -> Calendar:
        """Build and return the calendar.

        Returns:
            Calendar: The constructed calendar object.
        """
        logger.debug("Calendar build complete")
        return self.calendar

    def to_ical(self) -> bytes:
        """Convert the calendar to ICS format.

        Returns:
            bytes: The ICS formatted calendar data.
        """
        logger.debug("Converting calendar to ICS format")
        return self.calendar.to_ical()  # type: ignore[no-any-return]
