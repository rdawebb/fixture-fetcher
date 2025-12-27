"""CLI application for building football fixtures ICS calendars"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.backend import FootballDataRepository
from src.backend.config import get_config
from src.backend.storage.snapshot import diff_changes, load_snapshot, save_snapshot
from src.logic.calendar.ics_writer import ICSWriter
from src.logic.fixtures.enrich import enrich_all
from src.logic.fixtures.filters import Filter
from src.utils import (
    get_logger,
    InvalidInputError,
    TeamNotFoundError,
    TeamsCacheError,
)


logger = get_logger(__name__)

config = get_config()
CACHE_DIR = Path(config.get("CACHE_DIR", "data/cache/"))
CACHE_PATH = Path(config.get("CACHE_PATH", "data/cache/teams.yaml"))
TV_OVERRIDES_PATH = Path(
    config.get("TV_OVERRIDES_PATH", "data/overrides/tv_overrides.yaml")
)


def _slug(s: str) -> str:
    """Convert a club name to a slug format

    Args:
        s (str): Input string to convert

    Returns:
        str: Slugified string
    """
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")


def build(
    team: Optional[str] = None,
    competitions: Optional[list[str]] = None,
    season: Optional[int] = None,
    home_only: bool = False,
    away_only: bool = False,
    televised_only: bool = False,
    output: Path = Path("public"),
    tv_from: str = "auto",  # not used currently
    overrides: Optional[Path] = TV_OVERRIDES_PATH,
    cache_dir: Path = CACHE_DIR,
    refresh_cache: bool = False,
    refresh_competitions: bool = False,  # not used currently
    summarise: bool = True,
) -> None:
    """Build ICS calendar files for football fixtures.

    Args:
        team (Optional[str]): Team name to build calendar for.
        competition (Optional[list[str]]): Competition code to filter fixtures.
        season (Optional[int]): Season year (e.g., 2025 for 2025/26 season).
        home_only (bool): Whether to include only home fixtures.
        away_only (bool): Whether to include only away fixtures.
        televised_only (bool): Whether to include only fixtures with TV info.
        output (Path): Output directory for ICS files.
        tv_from (str): Source for TV info: 'auto', 'club_ics', or 'overrides'.
        overrides (Optional[Path]): Overrides YAML file path.
        refresh_cache (bool): Whether to refresh the local team cache from the API.
        refresh_competitions (bool): Whether to refresh the local competitions cache from the API.
        summarise (bool): Whether to print a summary of changes.

    Raises:
        InvalidInputError: If neither team nor all_teams is specified.
    """
    output.mkdir(parents=True, exist_ok=True)
    comps = [c.strip() for c in competitions if c.strip()] if competitions else []

    repo = FootballDataRepository()
    if refresh_cache:
        repo.client.refresh_team_cache()

    if not team:
        raise InvalidInputError("Team must be specified.")
    teams = [team]

    for t in teams:
        try:
            league = get_team_league(t)

            fixtures = repo.fetch_fixtures(t, comps, season)
            fixtures = Filter.apply_filters(fixtures, scheduled_only=True)

            if fixtures:
                comp_name = fixtures[0].competition
                comp_slug = _slug(comp_name)
            else:
                comp_slug = _slug(competitions) if competitions else "all"

            team_slug = _slug(t)
            snap_path = (
                cache_dir
                / "snapshots"
                / league
                / team_slug
                / f"{team_slug}.{comp_slug}.json"
            )
            prev = load_snapshot(snap_path)

            stats = enrich_all(fixtures, overrides_path=overrides)

            if home_only:
                fixtures = Filter.only_home(fixtures)
            if away_only:
                fixtures = Filter.only_away(fixtures)
            if televised_only:
                fixtures = Filter.only_televised(fixtures)

            team_output_dir = output / league / team_slug
            team_output_dir.mkdir(parents=True, exist_ok=True)

            fname = f"{team_slug}.{comp_slug}.ics"
            writer = ICSWriter(fixtures)
            writer.write(team_output_dir / fname)
            logger.info(
                f"Wrote {len(fixtures)} fixtures for team '{t}' to {team_output_dir / fname}"
            )

            if summarise:
                changes = diff_changes(fixtures, prev)
                print(
                    f"[{t}] fixtures: {len(fixtures)}\n"
                    f"🔄 Changes since last update: {changes['time']} time, {changes['venue']} venue, {changes['status']} status\n"
                    f"📺 TV info added: {stats['tv_overrides_applied']}"
                )

            save_snapshot(fixtures, snap_path)

        except (TeamNotFoundError, TeamsCacheError) as e:
            logger.error(f"Failed to build ICS for team '{t}': {e}")

        except Exception as e:
            logger.error(f"Failed to build ICS for team '{t}': {e}")


def cache_teams(
    competitions: list[str],
    output: Path = CACHE_PATH,
) -> None:
    """Cache team data for specified competitions.

    Args:
        competitions (list[str]): List of competition codes.
        output (Path): Path to cache the team data.
    """
    repo = FootballDataRepository()
    comps = [c.strip() for c in competitions if c.strip()]
    repo.client.refresh_team_cache(comps, cache_path=output)
    print(f"✅ Cached teams to {output}")


def get_team_league(team_name: str, cache_path: Path = CACHE_PATH) -> str:
    """Get the primary league for a given team.

    Args:
        team_name (str): Name of the team.
        cache_path (Path): Path to the team cache file.

    Returns:
        str: The primary league of the team.

    Raises:
        TeamNotFoundError: If the team is not found in the cache.
        TeamsCacheError: If there is an error loading the cache.
    """
    import yaml

    try:
        with open(cache_path) as f:
            teams_data = yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        raise TeamsCacheError(
            f"Error loading teams cache from {cache_path}",
            context={"error": str(e), "cache_path": str(cache_path)},
        )

    for league, teams in teams_data.items():
        if team_name in teams:
            return league

    raise TeamNotFoundError(
        f"Team '{team_name}' not found in cache",
        context={"team_name": team_name, "cache_path": str(cache_path)},
    )
