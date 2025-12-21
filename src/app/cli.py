from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.backend import FootballDataRepository
from src.backend.storage.snapshot import diff_changes, load_snapshot, save_snapshot
from src.logic import Filter, ICSWriter, enrich_all
from src.utils.logging import get_logger


logger = get_logger(__name__)


def _slug(s: str) -> str:
    """Convert a club name to a slug format."""
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
    overrides: Optional[Path] = Path("data/overrides/tv_overrides.yaml"),
    cache_dir: Path = Path("data/cache"),
    refresh_cache: bool = False,
    refresh_competitions: bool = False,  # not used currently
    summarise: bool = True,
) -> None:
    """Build ICS calendar files for football fixtures.

    Args:
        team (Optional[str]): Team name to build calendar for.
        all_teams (bool): Whether to build calendar for all teams.
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
    """
    output.mkdir(parents=True, exist_ok=True)
    comps = [c.strip() for c in competitions if c.strip()] if competitions else []

    repo = FootballDataRepository()
    if refresh_cache:
        repo.client.refresh_team_cache()

    if not team:
        logger.error("Team must be specified.")
        return
    teams = [team]

    for t in teams:
        try:
            fixtures = repo.fetch_fixtures(t, comps, season)
            fixtures = Filter.apply_filters(fixtures, scheduled_only=True)

            snap_path = cache_dir / f"{_slug(t)}.{_slug(competitions or 'all')}.json"
            prev = load_snapshot(snap_path)

            stats = enrich_all(fixtures, overrides_path=overrides)

            if home_only:
                fixtures = Filter.only_home(fixtures)
            if away_only:
                fixtures = Filter.only_away(fixtures)
            if televised_only:
                fixtures = Filter.only_televised(fixtures)

            if fixtures:
                comp_name = fixtures[0].competition
                comp_slug = _slug(comp_name)
            else:
                comp_slug = _slug(competitions) if competitions else "all"

            team_slug = _slug(t)
            team_output_dir = output / team_slug / comp_slug
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

        except Exception as e:
            logger.error(f"Failed to build ICS for team '{t}': {e}")


def cache_teams(
    competitions: list[str],
    output: Path = Path("data/teams.yaml"),
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
