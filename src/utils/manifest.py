"""Generate a manifest of available ICS calendars."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils import get_logger

logger = get_logger(__name__)


def generate_manifest(calendars_dir: Path, output_file: Path) -> None:
    """Generate a JSON manifest of available ICS calendars.

    Scans the calendars directory structure and creates a manifest file
    that lists all available calendars organized by league and team.

    Args:
        calendars_dir: Path to the calendars directory (e.g., public/calendars)
        output_file: Path where the manifest JSON file will be written
    """
    if not calendars_dir.exists():
        logger.warning(f"Calendars directory not found: {calendars_dir}")
        return

    manifest: dict[str, Any] = {"calendars": []}
    league_teams: dict[str, dict[str, Any]] = {}

    # Scan directory structure
    for league_dir in sorted(calendars_dir.iterdir()):
        if not league_dir.is_dir():
            continue

        league_slug = league_dir.name
        league_name = _unslug(league_slug)

        for team_dir in sorted(league_dir.iterdir()):
            if not team_dir.is_dir():
                continue

            team_slug = team_dir.name
            team_name = _unslug(team_slug)

            competitions: list[dict[str, str]] = []

            # Find all ICS files for team
            for ics_file in sorted(team_dir.glob(f"{team_slug}.*.ics")):
                parts = ics_file.stem.split(".")
                if len(parts) >= 2:
                    comp_code_slug = ".".join(parts[1:])
                    comp_code = _unslug(comp_code_slug, uppercase=True)
                    comp_name = _get_competition_name(comp_code)

                    # Create relative URL path from public directory
                    rel_path = ics_file.relative_to(calendars_dir.parent)
                    url = str(rel_path).replace("\\", "/")

                    competitions.append(
                        {
                            "code": comp_code,
                            "name": comp_name,
                            "url": url,
                        }
                    )

            if competitions:
                if league_slug not in league_teams:
                    league_teams[league_slug] = {
                        "league_name": league_name,
                        "teams": [],
                    }

                league_teams[league_slug]["teams"].append(
                    {
                        "name": team_name,
                        "slug": team_slug,
                        "competitions": competitions,
                    }
                )

    # Convert to list
    for league_slug in sorted(league_teams.keys()):
        league_data = league_teams[league_slug]
        manifest["calendars"].append(
            {
                "league": league_data["league_name"],
                "slug": league_slug,
                "teams": league_data["teams"],
            }
        )

    # Create manifest file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Generated calendar manifest at {output_file}")
    logger.debug(f"Manifest contains {len(manifest['calendars'])} league(s)")


def _unslug(slug: str, uppercase: bool = False) -> str:
    """Convert a slug back to a human-readable name.

    Args:
        slug: The slugified string (e.g., "premier-league")
        uppercase: If True, uppercase the first letter of each word

    Returns:
        Human-readable name (e.g., "Premier League")
    """
    words = slug.replace("-", " ").split()
    if uppercase:
        return " ".join(word.upper() for word in words)
    return " ".join(word.capitalize() for word in words)


def _get_competition_name(code: str) -> str:
    """Get the full competition name for a code.

    Args:
        code: Competition code

    Returns:
        Full competition name
    """
    competition_names = {"PL": "Premier League"}
    return competition_names.get(code, code)
