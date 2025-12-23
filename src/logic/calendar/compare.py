"""Compare two ICS calendar files for upcoming events"""

from datetime import datetime
from pathlib import Path
from typing import Set

from icalendar import Calendar

from src.utils import DataProcessingError, ICSReadError, get_logger

logger = get_logger(__name__)


class CalendarComparison:
    """Class to compare two ICS calendar files for upcoming events"""

    def get_upcoming_events(self, ics_file: Path) -> Set[tuple]:
        """Get upcoming events from an ICS file as a tuple

        Args:
            ics_file (Path): Path to the ICS file

        Returns:
            Set of (UID, DTSTART, DESCRIPTION) tuples for upcoming events
        """
        try:
            with open(ics_file, "rb") as f:
                cal = Calendar.from_ical(f.read())
        except Exception as e:
            logger.error(f"Error reading {ics_file}: {e}")
            raise ICSReadError(f"Error reading ICS file {ics_file}: {e}") from e

        now = datetime.now().astimezone()

        upcoming_events = set()
        try:
            for event in cal.walk():
                if event.name == "VEVENT":
                    dtstart = event.get("DTSTART")
                    if dtstart is not None and dtstart.dt.astimezone() > now:
                        upcoming_events.add(
                            (
                                str(event.get("UID", "")),
                                str(dtstart.dt.astimezone()),
                                str(event.get("DESCRIPTION", "")),
                            )
                        )
        except Exception as e:
            logger.error(f"Error processing events in {ics_file}: {e}")
            raise DataProcessingError(
                f"Error processing events in {ics_file}: {e}"
            ) from e

        return upcoming_events

    def compare_calendars(self, old_dir: Path, new_dir: Path) -> bool:
        """Compare two directories of ICS calendar files for upcoming events

        Args:
            old_dir (Path): Path to directory of old ICS files
            new_dir (Path): Path to directory of new ICS files

        Returns:
            bool: True if upcoming events differ, False if the same
        """
        old_signature = set()
        new_signature = set()

        for ics_file in sorted(old_dir.glob("*.ics")):
            try:
                old_signature.update(self.get_upcoming_events(ics_file))
            except (ICSReadError, DataProcessingError) as e:
                logger.warning(f"Error processing {ics_file}: {e}")

        for ics_file in sorted(new_dir.glob("*.ics")):
            try:
                new_signature.update(self.get_upcoming_events(ics_file))
            except (ICSReadError, DataProcessingError) as e:
                logger.warning(f"Error processing {ics_file}: {e}")

        return old_signature != new_signature
