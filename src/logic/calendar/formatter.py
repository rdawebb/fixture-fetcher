"""Module to format fixtures into iCalendar events."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from icalendar import Event

from logic.fixtures.models import Fixture
from utils import FFLogger

logger = FFLogger.get_logger(__name__)

LONDON_TZ = ZoneInfo("Europe/London")


class EventFormatter:
    """Class to format fixtures into iCalendar events."""

    @staticmethod
    def _uid(f: Fixture) -> str:
        """Generate a unique ID for the fixture

        Args:
            f: The Fixture object to generate a UID for.

        Returns:
            A unique ID for the fixture.
        """
        return f"{f.id}@fixture-fetcher"

    @classmethod
    def format_event(cls, fixture: Fixture) -> Event | None:
        """Format a Fixture object as an iCalendar Event.

        Args:
            fixture: The Fixture object to format.

        Returns:
            An iCalendar Event object, or None if the fixture has no kick-off
            date and so cannot produce a valid VEVENT.
        """
        if fixture.utc_kickoff is None:
            logger.warning(
                f"Skipping fixture {fixture.id} "
                f"({fixture.home_team} vs {fixture.away_team}): no kick-off date"
            )
            return None

        event = Event()
        event.add("uid", cls._uid(fixture))
        # Required by RFC 5545 for every VEVENT
        event.add("dtstamp", datetime.now(timezone.utc))

        start = fixture.utc_kickoff.astimezone(LONDON_TZ)
        event.add("dtstart", start)
        event.add("dtend", start + timedelta(hours=2))
        event.add("summary", f"{fixture.home_team} vs {fixture.away_team}")

        parts = [fixture.competition_code]

        if fixture.tv is not None:
            parts.append(f"{fixture.tv}")

        if fixture.matchday is not None:
            parts.append(f"Matchday {fixture.matchday}")

        if fixture.venue:
            parts.append(f"{fixture.venue}")
            event.add("location", fixture.venue)

        event.add("description", " | ".join(parts))

        return event
