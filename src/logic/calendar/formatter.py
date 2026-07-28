"""Module to format fixtures into iCalendar events."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from icalendar import Event

from logic.fixtures.models import Fixture
from utils import FFLogger

logger = FFLogger.get_logger(__name__)

LONDON_TZ = ZoneInfo("Europe/London")

# football-data.org match status -> RFC 5545 STATUS (section 3.8.1.11)
# Statuses not listed here (FINISHED, IN_PLAY, etc) get no STATUS property
ICS_STATUS = {
    "TIMED": "CONFIRMED",  # Kick-off time confirmed
    "SCHEDULED": "TENTATIVE",  # Date known, kick-off time provisional
    "POSTPONED": "CANCELLED",
    "SUSPENDED": "CANCELLED",
    "CANCELLED": "CANCELLED",
}

# Not every client renders a CANCELLED event distinctly, some hide it entirely,
# so the status is spelled out in the description as well
STATUS_LABEL = {
    "SCHEDULED": "Kick-off time TBC",
    "POSTPONED": "Postponed",
    "SUSPENDED": "Suspended",
    "CANCELLED": "Cancelled",
}


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

        ics_status = ICS_STATUS.get(fixture.status)
        if ics_status:
            event.add("status", ics_status)

        parts = [fixture.competition_code]

        label = STATUS_LABEL.get(fixture.status)
        if label:
            parts.append(label)

        if fixture.tv is not None:
            parts.append(f"{fixture.tv}")

        if fixture.matchday is not None:
            parts.append(f"Matchday {fixture.matchday}")

        if fixture.venue:
            parts.append(f"{fixture.venue}")
            event.add("location", fixture.venue)

        event.add("description", " | ".join(parts))

        return event
