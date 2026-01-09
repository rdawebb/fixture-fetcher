from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml

from src.logic.fixtures.models import Fixture
from src.utils import get_logger

logger = get_logger(__name__)


def apply_overrides(fixtures: List[Fixture], overrides_path: Path) -> int:
    """Apply overrides from a YAML file to the list of fixtures.

    Args:
        fixtures (List[Fixture]): The list of Fixture objects to apply overrides to.
        overrides_path (Path): The path to the YAML file containing overrides.

    Returns:
        int: The number of overrides applied.
    """
    if not overrides_path or not overrides_path.exists():
        logger.warning("Overrides file does not exist")
        return 0

    data = yaml.safe_load(overrides_path.read_text()) or {}
    by_id = {f.id: f for f in fixtures}

    applied = 0
    for key, val in data.items():
        key = str(key)
        tv = (val or {}).get("tv")
        if not tv:
            continue
        if key in by_id:
            if not by_id[key].tv:
                applied += 1
            by_id[key].tv = tv
            logger.debug(f"Applied TV override for fixture ID {key}: {tv}")
            continue

        for f in fixtures:
            if f.utc_kickoff is None:
                continue

            comp = f"{f.utc_kickoff.date()}:{f.home_team}:{f.away_team}"
            if comp == key:
                if not f.tv:
                    applied += 1
                f.tv = tv
                logger.debug(f"Applied TV override for fixture {comp}: {tv}")
                break

    return applied


def enrich_all(
    fixtures: List[Fixture],
    overrides_path: Optional[Path] = None,
) -> dict:
    """Enrich fixtures with TV info from club ICS calendars and apply overrides.

    Args:
        fixtures (List[Fixture]): The list of Fixture objects to enrich.
        club_ics_urls (Optional[str]): Path to YAML file with club ICS URLs.
        overrides_path (Optional[Path]): Path to YAML file with overrides.

    Returns:
        dict: A summary of the enrichment process.
    """
    before_tv = sum(1 for f in fixtures if (f.tv or "").strip())
    applied = 0

    if overrides_path:
        try:
            applied = apply_overrides(fixtures, overrides_path) if overrides_path else 0
            logger.info("Applied overrides successfully")
        except Exception as e:
            logger.error(f"Failed to apply overrides: {e}")

    after_tv = sum(1 for f in fixtures if (f.tv or "").strip())

    return {
        "tv_overrides_applied": applied,
        "tv_before": before_tv,
        "tv_after": after_tv,
    }
