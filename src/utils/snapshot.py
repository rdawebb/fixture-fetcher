"""Utility functions for snapshotting and comparing Fixture data."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple, cast

from src.models import Fixture
from src.utils.errors import DataProcessingError

logger = logging.getLogger(__name__)


def _fixture_to_dict(fixture: Fixture) -> dict:
    """Convert a Fixture object to a dictionary for snapshotting.

    Args:
        fixture (Fixture): The Fixture object to convert.

    Returns:
        dict: A dictionary representation of the Fixture.
    """
    dict = asdict(fixture)
    dict["utc_kickoff"] = fixture.utc_kickoff.isoformat() if fixture.utc_kickoff else None
    return dict


def _dict_to_key_fields(d: dict) -> Tuple[str, str, str]:
    """Extract key fields from a fixture dictionary for comparison.

    Args:
        d (dict): The fixture dictionary.

    Returns:
        Tuple[str, str, str]: A tuple of (kickoff, venue, status).
    """
    return (
        d.get("utc_kickoff", ""),
        d.get("venue", ""),
        d.get("status", ""),
    )


def save_snapshot(fixtures: List[Fixture], path: Path) -> None:
    """Save a snapshot of fixtures to a JSON file.

    Args:
        fixtures (List[Fixture]): The list of Fixture objects to snapshot.
        path (Path): The path to the JSON file to save the snapshot.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {f.id: _fixture_to_dict(f) for f in fixtures}
    try:
        path.write_text(json.dumps(snapshot, indent=2, sort_keys=True))
        logger.info(f"Snapshot saved to {path} with {len(fixtures)} fixtures.")
    except Exception as e:
        logger.error(f"Failed to save snapshot to {path}: {e}", exc_info=True)
        raise DataProcessingError("Failed to save snapshot") from e


def load_snapshot(path: Path) -> Dict[str, dict]:
    """Load a snapshot of fixtures from a JSON file.

    Args:
        path (Path): The path to the JSON file containing the snapshot.

    Returns:
        Dict[str, dict]: A dictionary mapping fixture IDs to their snapshot dictionaries.
    """
    if not path.exists():
        logger.warning(f"Snapshot file {path} does not exist.")
        return {}
    try:
        return cast(Dict[str, dict], json.loads(path.read_text()))
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from snapshot file {path}: {e}")
        return {}


def diff_changes(current: List[Fixture], snapshot: Dict[str, dict]) -> Dict[str, int]:
    """Compare current fixtures to a snapshot and identify changes.

    Args:
        current (List[Fixture]): The current list of Fixture objects.
        snapshot (Dict[str, dict]): The snapshot dictionary mapping fixture IDs to their data.

    Returns:
        Dict[str, int]: A dictionary with counts of 'time', 'venue', and 'status' changes.
    """
    counts = {"time": 0, "venue": 0, "status": 0}
    for f in current:
        prev = snapshot.get(f.id)
        if not prev:
            continue
        curr_tuple = (
            f.utc_kickoff.isoformat() if f.utc_kickoff else "",
            f.venue or "",
            f.status or "",
        )

        prev_tuple = _dict_to_key_fields(prev)

        if curr_tuple[0] != prev_tuple[0]:
            counts["time"] += 1
        if curr_tuple[1] != prev_tuple[1]:
            counts["venue"] += 1
        if curr_tuple[2] != prev_tuple[2]:
            counts["status"] += 1

    logger.info(f"Diff changes: {counts}")
    return counts
