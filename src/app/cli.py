"""CLI application for building football fixtures ICS calendars"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from backend import FootballDataRepository
from backend.config import get_config
from backend.storage.snapshot import diff_changes, load_snapshot, save_snapshot
from logic.calendar.ics_writer import ICSWriter
from logic.fixtures.enrich import enrich_all
from logic.fixtures.filters import Filter
from utils import (
    get_logger,
    CalendarError,
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
) -> dict:
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

    Returns:
        dict: Summary of the build process with keys:
            - successful: List of (team_name, competition_name) tuples
            - failed: List of (team_name, error_message) tuples
            - total: Total number of teams attempted

    Raises:
        InvalidInputError: If neither team nor all_teams is specified.
    """
    output.mkdir(parents=True, exist_ok=True)
    comps = [c.strip() for c in competitions if c.strip()] if competitions else []

    repo = FootballDataRepository()

    if refresh_cache or not CACHE_PATH.exists():
        repo.client.refresh_team_cache()

    if not team:
        raise InvalidInputError("Team must be specified")
    teams = [team]

    successful = []
    failed = []

    for t in teams:
        try:
            league, short_name = get_team_info(t)
        except (TeamNotFoundError, TeamsCacheError) as e:
            error_msg = str(e)
            logger.error(f"Failed to build ICS for team '{t}': {error_msg}")
            failed.append((t, error_msg))
            continue

        try:
            league_slug = _slug(league)

            fixtures = repo.fetch_fixtures(t, comps, season)
            fixtures = Filter.apply_filters(fixtures, scheduled_only=True)

            fixtures_by_comp = {}
            for fixture in fixtures:
                comp_code = fixture.competition_code
                if comp_code not in fixtures_by_comp:
                    fixtures_by_comp[comp_code] = []
                fixtures_by_comp[comp_code].append(fixture)

            for comp_code, comp_fixtures in fixtures_by_comp.items():
                if not comp_fixtures:
                    logger.warning(
                        f"No '{comp_code}' fixtures found for '{short_name}', skipping..."
                    )
                    continue

                try:
                    comp_name = comp_fixtures[0].competition
                    team_slug = _slug(short_name)
                    comp_code_slug = _slug(comp_code)

                    snap_path = (
                        cache_dir
                        / "snapshots"
                        / league_slug
                        / team_slug
                        / f"{team_slug}.{comp_code_slug}.json"
                    )
                    prev = load_snapshot(snap_path)

                    stats = enrich_all(comp_fixtures, overrides_path=overrides)

                    filtered_fixtures = comp_fixtures[:]
                    if home_only:
                        filtered_fixtures = Filter.only_home(filtered_fixtures)
                    if away_only:
                        filtered_fixtures = Filter.only_away(filtered_fixtures)
                    if televised_only:
                        filtered_fixtures = Filter.only_televised(filtered_fixtures)

                    team_output_dir = output / league_slug / team_slug
                    team_output_dir.mkdir(parents=True, exist_ok=True)

                    fname = f"{team_slug}.{comp_code_slug}.ics"
                    writer = ICSWriter(filtered_fixtures)
                    output_file = writer.write(team_output_dir / fname)
                    logger.info(
                        f"Wrote {len(filtered_fixtures)} fixtures for team '{short_name}' in {comp_code} to {output_file}"
                    )
                    successful.append((short_name, comp_code))

                    if summarise:
                        changes = diff_changes(comp_fixtures, prev)
                        print(
                            f"[{short_name}] - {comp_code} fixtures: {len(comp_fixtures)}\n"
                            f"🔄 Changes since last update: {changes['time']} time, {changes['venue']} venue, {changes['status']} status\n"
                            f"📺 TV info added: {stats['tv_overrides_applied']}"
                        )

                    save_snapshot(comp_fixtures, snap_path)

                except Exception as e:
                    raise CalendarError(
                        f"Failed to build calendar for {comp_name}",
                        context={
                            "team": short_name,
                            "competition": comp_name,
                            "error": str(e),
                        },
                    ) from e

        except CalendarError as e:
            error_msg = str(e)
            logger.error(
                f"Failed to build ICS for team '{short_name}' in {comp_name}: {error_msg}"
            )
            failed.append((short_name, comp_code))

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to build ICS for team '{short_name}': {error_msg}")
            failed.append((short_name, error_msg))

    return {
        "successful": successful,
        "failed": failed,
        "total": len(teams),
    }


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
    print("✅ Cached teams successfully")


def get_team_info(team_name: str, cache_path: Path = CACHE_PATH) -> tuple[str, str]:
    """Get the primary league and short name for a given team.

    Args:
        team_name (str): Name of the team.
        cache_path (Path): Path to the team cache file.

    Returns:
        tuple[str, str]: The primary league and short name of the team.

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
        if not isinstance(teams, dict):
            logger.warning(
                f"Invalid cache structure for league '{league}': expected dict, got {type(teams).__name__}"
            )
            continue
        if team_name in teams:
            team_info = teams[team_name]
            short_name = team_name  # Default to team_name
            if isinstance(team_info, dict) and "short_name" in team_info:
                short_name = team_info["short_name"]
            else:
                logger.warning(
                    f"No short name found for team '{team_name}' in league '{league}'"
                )

            return league, short_name

    raise TeamNotFoundError(
        f"Team '{team_name}' not found in cache",
        context={"team_name": team_name, "cache_path": str(cache_path)},
    )
