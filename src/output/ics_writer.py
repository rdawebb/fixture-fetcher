

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

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
        for f in self.fixtures:
            ev = Event()
            ev.add("uid", self._uid(f))
            title = f"{f.home_team} vs {f.away_team}"
                
            if f.utc_kickoff:
                start = f.utc_kickoff.astimezone(LONDON_TZ)
                ev.add("dtstart", start)
                ev.add("dtend", start + timedelta(hours=2))
                ev.add("summary", title)
                    
                parts = [f.competition]

                if f.matchday:
                    parts.append(f"Matchday {f.matchday}")
                    
                if f.venue:
                    parts.append(f"Venue: {f.venue}")
                    ev.add("location", f.venue)

                ev.add("description", " | ".join(parts))
                
            else:
                ev.add("summary", f"{title} (KO TBD)")
                ev.add("description", f"{f.competition} | Kick-off time TBC")

            logger.debug(f"Adding event: {title}")
            self.calendar.add_component(ev)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(self.calendar.to_ical())
            logger.info(f"ICS file successfully written to {path}")

        except Exception as e:
            logger.error(f"Error writing ICS file: {e}")
            raise ICSWriteError(f"Error writing ICS file: {e}")

        return path
            