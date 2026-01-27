"""Utility functions for snapshotting and comparing Fixture data."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple, cast

from logic.fixtures.models import Fixture
from utils import DataProcessingError, get_logger

logger = get_logger(__name__)


def _fixture_to_dict(fixture: Fixture) -> dict:
    """Convert a Fixture object to a dictionary for snapshotting.

    Args:
        fixture: The Fixture object to convert.

    Returns:
        A dictionary representation of the Fixture.
    """
    dict = asdict(fixture)
    dict["utc_kickoff"] = (
        fixture.utc_kickoff.isoformat() if fixture.utc_kickoff else None
    )
    return dict


def _dict_to_key_fields(d: dict) -> Tuple[str, str, str, str]:
    """Extract key fields from a fixture dictionary for comparison.

    Args:
        d: The fixture dictionary.

    Returns:
        A tuple of (kickoff, venue, tv, status).
    """
    return (
        d.get("utc_kickoff", "") or "",
        d.get("venue") or "",
        d.get("tv", "") or "",
        d.get("status", "") or "",
    )


def save_snapshot(fixtures: List[Fixture], path: Path) -> None:
    """Save a snapshot of fixtures to a JSON file.

    Args:
        fixtures: The list of Fixture objects to snapshot.
        path: The path to the JSON file to save the snapshot.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {f.id: _fixture_to_dict(f) for f in fixtures}
    try:
        path.write_text(json.dumps(snapshot, indent=2, sort_keys=True))
        logger.info(f"Snapshot saved successfully with {len(fixtures)} fixtures.")
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}", exc_info=True)
        raise DataProcessingError("Failed to save snapshot") from e


def load_snapshot(path: Path) -> Dict[str, dict]:
    """Load a snapshot of fixtures from a JSON file.

    Args:
        path: The path to the JSON file containing the snapshot.

    Returns:
        A dictionary mapping fixture IDs to their snapshot dictionaries.
    """
    if not path.exists():
        logger.warning("Snapshot file does not exist.")
        return {}
    try:
        return cast(Dict[str, dict], json.loads(path.read_text()))
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from snapshot file: {e}")
        return {}


def diff_changes(current: List[Fixture], snapshot: Dict[str, dict]) -> Dict[str, int]:
    """Compare current fixtures to a snapshot and identify changes.

    Args:
        current: The current list of Fixture objects.
        snapshot: The snapshot dictionary mapping fixture IDs to their data.

    Returns:
        A dictionary with counts of 'time', 'venue', 'tv', and 'status' changes.
    """
    counts = {"time": 0, "venue": 0, "tv": 0, "status": 0}
    for f in current:
        prev = snapshot.get(f.id)
        if not prev:
            continue
        curr_tuple = (
            f.utc_kickoff.isoformat() if f.utc_kickoff else "",
            f.venue or "",
            f.tv or "",
            f.status or "",
        )

        prev_tuple = _dict_to_key_fields(prev)

        if curr_tuple[0] != prev_tuple[0]:
            counts["time"] += 1
        if curr_tuple[1] != prev_tuple[1]:
            counts["venue"] += 1
        if curr_tuple[2] != prev_tuple[2]:
            counts["tv"] += 1
        if curr_tuple[3] != prev_tuple[3]:
            counts["status"] += 1

    logger.info(f"Diff changes: {counts}")
    return counts
