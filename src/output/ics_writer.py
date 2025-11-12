from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from icalendar import Calendar, Event
from zoneinfo import ZoneInfo

from src.models import Fixture
from src.utils.errors import ICSWriteError

LONDON_TZ = ZoneInfo("Europe/London")


class ICSWriter:
    """Class to write fixtures to an ICS file."""

    def __init__(self, fixtures: Iterable[Fixture]) -> None:
        """Initialize the ICSWriter with a list of fixtures.

        Args:
            fixtures (Iterable[Fixture]): An iterable of Fixture objects.
        """
        self.fixtures = fixtures
        self.calendar = Calendar()
        self.calendar.add("prodid", "-//Football Fixture Fetcher//mxm.dk//EN")
        self.calendar.add("version", "2.0")

    def _uid(self, f: Fixture) -> str:
        return f"{f.id}@football-fixture-fetcher"

    def write(self, path: Path) -> Path:
        """Convert fixtures to an ICS file and save it.

        Args:
            path (Path): The file path to save the ICS file.

        Returns:
            Path: The path to the saved ICS file.

        Raises:
            ICSWriteError: If there is an error writing the ICS file.
        """
        logger = logging.getLogger(__name__)
        logger.info(f"Starting ICS file write to {path}")
        for fixture in self.fixtures:
            ev = Event()
            ev.add("uid", self._uid(fixture))
            title = f"{fixture.home_team} vs {fixture.away_team}"

            if fixture.utc_kickoff:
                start = fixture.utc_kickoff.astimezone(LONDON_TZ)
                ev.add("dtstart", start)
                ev.add("dtend", start + timedelta(hours=2))
                ev.add("summary", title)

                parts = [fixture.competition]

                if fixture.matchday:
                    parts.append(f"Matchday {fixture.matchday}")

                if fixture.venue:
                    parts.append(f"Venue: {fixture.venue}")
                    ev.add("location", fixture.venue)

                ev.add("description", " | ".join(parts))

            else:
                ev.add("summary", f"{title} (KO TBD)")
                ev.add("description", f"{fixture.competition} | Kick-off time TBC")

            logger.debug(f"Adding event: {title}")
            self.calendar.add_component(ev)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as file_handle:
                file_handle.write(self.calendar.to_ical())
            logger.info(f"ICS file successfully written to {path}")

        except Exception as e:
            logger.error(f"Error writing ICS file: {e}")
            raise ICSWriteError(f"Error writing ICS file: {e}") from e

        return path
