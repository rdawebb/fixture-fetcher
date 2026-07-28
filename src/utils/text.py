"""Text helpers shared across the app."""

from __future__ import annotations


def slugify(s: str) -> str:
    """Convert a club name to a slug format

    Args:
        s: Input string to convert

    Returns:
        Slugified string
    """
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")
