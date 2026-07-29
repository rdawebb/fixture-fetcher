"""Generate a manifest of available ICS calendars."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import orjson
import yaml
from icalendar import Calendar

from utils import (
    FFLogger,
    as_datetime,
    is_legible,
    is_valid_hex,
    parse_club_colors,
    slugify,
    text_on,
)

logger = FFLogger.get_logger(__name__)


def load_color_overrides(path: Path) -> dict[str, str]:
    """Load curated accent colours, flattening the per-league grouping.

    A missing or malformed file is not fatal — the build falls back to colours
    derived from the API's club colours.

    Args:
        path: Path to the team colours YAML file.

    Returns:
        Mapping of team name to a validated #RRGGBB colour.
    """
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}

    except (OSError, yaml.YAMLError) as e:
        logger.warning(f"Could not read team colours from {path}: {e}")
        return {}

    overrides: dict[str, str] = {}

    for league, teams in data.items():
        if not isinstance(teams, dict):
            logger.warning(f"Skipping malformed team colours entry: {league}")
            continue

        for name, colour in teams.items():
            if not is_valid_hex(colour):
                logger.warning(f"Skipping invalid colour for '{name}': {colour!r}")
                continue

            # Honour the curator's choice, but flag anything that will be hard
            # to read as button text
            if not is_legible(colour):
                logger.warning(
                    f"Colour {colour} for '{name}' is below the 4.5:1 contrast "
                    "threshold and may be hard to read"
                )

            overrides[name] = colour

    return overrides


def generate_manifest(
    calendars_dir: Path,
    output_file: Path,
    team_cache: dict[str, Any] | None = None,
    color_overrides: dict[str, str] | None = None,
) -> None:
    """Generate a JSON manifest of available ICS calendars.

    Scans the calendars directory structure and creates a manifest file
    that lists all available calendars organized by league and team.

    When a team cache is supplied, each team also carries its real name, crest
    URL and accent colour. Without one the manifest falls back to un-slugging
    directory names and emits no colour or crest.

    Each team also carries the ISO 8601 timestamp of its next kick-off, read
    back out of the calendars being scanned.

    Args:
        calendars_dir: Path to the calendars directory (e.g., public/calendars)
        output_file: Path where the manifest JSON file will be written
        team_cache: Parsed contents of teams.yaml, keyed by league then team name
        color_overrides: Accent colour per team name, overriding the derived one
    """
    if not calendars_dir.exists():
        logger.warning(f"Calendars directory not found: {calendars_dir}")
        return

    manifest: dict[str, Any] = {"calendars": []}
    league_teams: dict[str, dict[str, Any]] = {}
    team_index = _index_teams_by_slug(team_cache)

    # One reference point for the whole manifest
    now = datetime.now().astimezone()

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
            record = team_index.get(team_slug, {})
            # Un-slugging mangles names ("man-utd", "afc-bournemouth"), so it is
            # only a fallback for teams missing from the cache
            team_name = record.get("name") or _unslug(team_slug)

            competitions: list[dict[str, str]] = []
            next_fixture: datetime | None = None

            # Find all ICS files for team
            for ics_file in sorted(team_dir.glob(f"{team_slug}.*.ics")):
                kickoff = _next_kickoff(ics_file, now)
                if kickoff and (next_fixture is None or kickoff < next_fixture):
                    next_fixture = kickoff

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

                team_entry: dict[str, Any] = {
                    "name": team_name,
                    "slug": team_slug,
                }

                colour = (color_overrides or {}).get(team_name) or parse_club_colors(
                    record.get("club_colors")
                )
                # Omit rather than emit nulls, so the page keeps its CSS default
                if colour:
                    team_entry["color"] = colour
                    team_entry["text_on_color"] = text_on(colour)

                if record.get("crest"):
                    team_entry["crest"] = record["crest"]

                # Absent during off-season
                if next_fixture:
                    team_entry["next_fixture"] = next_fixture.isoformat()

                team_entry["competitions"] = competitions
                league_teams[league_slug]["teams"].append(team_entry)

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
    with open(output_file, "wb") as f:
        f.write(orjson.dumps(manifest))

    logger.info(f"Generated calendar manifest at {output_file}")
    logger.debug(f"Manifest contains {len(manifest['calendars'])} league(s)")


def _next_kickoff(ics_file: Path, now: datetime) -> datetime | None:
    """Find the earliest upcoming kick-off in a calendar file.

    Called-off matches are kept in the feed, but are skipped here.

    Args:
        ics_file: Path to the ICS file to read.
        now: The moment fixtures are considered upcoming from.

    Returns:
        The earliest kick-off after `now`, or None if there is none.
    """
    earliest: datetime | None = None

    try:
        with open(ics_file, "rb") as f:
            cal = Calendar.from_ical(f.read())

        for event in cal.walk("VEVENT"):
            dtstart = event.get("DTSTART")
            if dtstart is None:
                continue

            if str(event.get("STATUS", "")).upper() == "CANCELLED":
                continue

            start = as_datetime(dtstart.dt)
            if start > now and (earliest is None or start < earliest):
                earliest = start

    # Best-effort metadata, so a bad file only costs this team its next-fixture line
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not read next fixture from {ics_file}: {e}")
        return None

    return earliest


def _index_teams_by_slug(
    team_cache: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Index cached teams by the slug used for their calendar directory.

    Calendar directories are named after the team's short name (see
    `app.cli.build`), so that is the primary key. The full name is indexed as
    a fallback for teams cached without a short name.

    Args:
        team_cache: Parsed contents of teams.yaml, keyed by league then team name

    Returns:
        Mapping of directory slug to a record carrying the team's full name,
        club colours and crest.
    """
    if not team_cache:
        return {}

    index: dict[str, dict[str, Any]] = {}

    for teams in team_cache.values():
        if not isinstance(teams, dict):
            continue

        for name, data in teams.items():
            data = data or {}
            record = {
                "name": name,
                "club_colors": data.get("club_colors"),
                "crest": data.get("crest"),
            }

            # Full name first so the short name wins where the two collide
            index.setdefault(slugify(name), record)
            index[slugify(data.get("short_name") or name)] = record

    return index


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
