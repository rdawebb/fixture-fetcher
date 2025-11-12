"""Module to enrich fixtures with TV information from club ICS calendars."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

import requests
from dateutil import parser as dtparse
from icalendar import Calendar

from src.models import Fixture

logger = logging.getLogger(__name__)

_session = requests.Session()

TV_PATTERN = re.compile(
    r"\b"
    r"Sky\s+Sports|TNT\s+Sport|BBC(?:\s+One|\s+Two)?|"
    r"ITV(?:\s*1|\s*4)?|Amazon\s+Prime|"
    r"BBC\s*iPlayer|ITV\s*X|Disney\+|"
    r"\b",
    re.IGNORECASE,
)


def _extract_tv_info(text: str) -> Optional[str]:
    """Extract TV information from a given text.

    Args:
        text (str): The text to extract TV information from.

    Returns:
        Optional[str]: The extracted TV information, or None if not found.
    """
    if not text:
        return None
    match = TV_PATTERN.search(text)
    if not match:
        return None

    return re.sub(r"\s+", " ", match.group(0)).title()


def _download_ics(url: str) -> bytes:
    """Download ICS data from a given URL.

    Args:
        url (str): The URL to download the ICS data from.

    Returns:
        bytes: The content of the ICS file.
    """
    url_https = url.replace("webcal://", "https://")
    response = _session.get(url_https, timeout=30)
    response.raise_for_status()

    return response.content


def enrich_from_club_ics(fixtures: list[Fixture], url: str) -> None:
    """Enrich fixtures with data from a club's ICS calendar.

    Args:
        fixtures (list[Fixture]): The list of Fixture objects to enrich.
        url (str): The URL of the club's ICS calendar.
    """
    try:
        ics_bytes = _download_ics(url)
        cal = Calendar.from_ical(ics_bytes)
    except Exception:
        logger.error(f"Failed to download or parse ICS from {url}")
        return

    events = [c for c in cal.walk() if c.name == "VEVENT"]

    enrich_count = 0
    for f in fixtures:
        if f.tv or f.utc_kickoff is None:
            continue
        for e in events:
            try:
                dtstart = e.get("dtstart").dt
                if not isinstance(dtstart, datetime):
                    dtstart = dtparse.parse(str(dtstart))
                if abs((f.utc_kickoff - dtstart).total_seconds()) > 3600:
                    continue

                summary = str(e.get("summary", ""))
                desc = str(e.get("description", ""))
                tv = _extract_tv_info(summary) or _extract_tv_info(desc)
                if tv:
                    f.tv = tv
                    logger.debug(f"Enriched fixture {f.id} with TV info: {tv}")
                    enrich_count += 1
                    break
            except Exception as e:
                logger.warning(f"Error processing event for fixture {f.id}: {e}")
                continue

    logger.info(f"Enriched {enrich_count} fixtures with TV info from ICS.")
