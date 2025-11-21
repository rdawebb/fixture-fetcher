"""Module to format fixtures into iCalendar events."""

from datetime import timedelta

from icalendar import Event
from zoneinfo import ZoneInfo

from src.logic.fixtures.models import Fixture

LONDON_TZ = ZoneInfo("Europe/London")


class EventFormatter:
    """Class to format fixtures into iCalendar events."""

    @staticmethod
    def _uid(f: Fixture) -> str:
        """Generate a unique ID for the fixture"""
        return f"{f.id}@fixture-fetcher"

    @classmethod
    def format_event(cls, fixture: Fixture) -> Event:
        event = Event()
        event.add("uid", cls._uid(fixture))
        title = f"{fixture.home_team} vs {fixture.away_team}"

        if fixture.utc_kickoff:
            start = fixture.utc_kickoff.astimezone(LONDON_TZ)
            event.add("dtstart", start)
            event.add("dtend", start + timedelta(hours=2))
            event.add("summary", title)

            parts = [fixture.competition_code]

            if fixture.tv is not None:
                parts.append(f"{fixture.tv}")

            if fixture.matchday is not None:
                parts.append(f"Matchday {fixture.matchday}")

            if fixture.venue:
                parts.append(f"{fixture.venue}")
                event.add("location", fixture.venue)

            event.add("description", " | ".join(parts))
        else:
            event.add("summary", f"{title} (TBC)")
            event.add("description", f"{fixture.competition_code} | Kickoff TBC")

        return event
