"""Date helpers shared across the app."""

from __future__ import annotations

from datetime import date, datetime, time


def as_datetime(value: date | datetime) -> datetime:
    """Normalise an ICS DTSTART value to an aware datetime.

    All-day events carry a plain `date`, which has no `astimezone`. Treat
    those as starting at local midnight so they compare against timed events.

    Args:
        value: The `DTSTART` value, either a date or a datetime.

    Returns:
        A timezone-aware datetime.
    """
    if not isinstance(value, datetime):
        value = datetime.combine(value, time.min)

    return value.astimezone()
