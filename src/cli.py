from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
import yaml

from src.config import LOG_FILE, LOG_LEVEL
from src.logic.enrich import enrich_all
from src.logic.filters import Filter
from src.output.ics_writer import ICSWriter
from src.providers.football_data import FDClient
from src.utils.snapshot import diff_changes, load_snapshot, save_snapshot

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)

app = typer.Typer(help="Football Fixture Fetcher CLI", add_completion=False)

logger = logging.getLogger(__name__)


def _slug(s: str) -> str:
    """Convert a club name to a slug format."""
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")


def _club_ics_url(team: str, mapping_path: Path) -> Optional[str]:
    """Get the ICS URL for a given club from a YAML mapping file."""
    if not mapping_path.exists():
        logger.warning(f"Club ICS mapping file {mapping_path} does not exist.")
        return None

    loaded_data = yaml.safe_load(mapping_path.read_text())
    data: dict[str, str] = loaded_data if isinstance(loaded_data, dict) else {}
    if team in data:
        url = data[team]
        return url if isinstance(url, str) else None

    for k, v in data.items():
        if k.lower() == team.lower().replace(" ", "_"):
            return v if isinstance(v, str) else None

    return None


@app.command()
def build(
    team: Optional[str] = typer.Option(None, help="Team name to build calendar for"),
    all_teams: bool = typer.Option(False, help="Build calendar for all teams"),
    competitions: Optional[str] = typer.Option(None, help="Competition code to filter fixtures"),
    season: Optional[int] = typer.Option(None, help="Season year (e.g., 2025 for 2025/26 season)"),
    home_only: bool = typer.Option(False, help="Include only home fixtures"),
    away_only: bool = typer.Option(False, help="Include only away fixtures"),
    televised_only: bool = typer.Option(False, help="Include only fixtures with TV info"),
    output: Path = typer.Option(Path("public"), help="Output directory for ICS files"),
    tv_from: str = typer.Option(
        "auto", help="Source for TV info: 'auto', 'club_ics', or 'overrides'"
    ),
    overrides: Optional[Path] = typer.Option(
        Path("data/tv_overrides.yaml"), help="Overrides YAML file path"
    ),
    club_ics_map: Path = typer.Option(
        Path("data/club_ics_urls.yaml"), help="Club ICS URLs mapping YAML file path"
    ),
    refresh_cache: bool = typer.Option(False, help="Refresh the local team cache from the API"),
    refresh_competitions: bool = typer.Option(
        False, help="Refresh the local competitions cache from the API"
    ),
    summarise: bool = typer.Option(True, help="Print change summary (recommended)"),
) -> None:
    """Build ICS calendar files for football fixtures.

    Args:
        team (Optional[str]): Team name to build calendar for.
        all_teams (bool): Whether to build calendar for all teams.
        competition (Optional[str]): Competition code to filter fixtures.
        season (Optional[int]): Season year (e.g., 2025 for 2025/26 season).
        home_only (bool): Whether to include only home fixtures.
        away_only (bool): Whether to include only away fixtures.
        televised_only (bool): Whether to include only fixtures with TV info.
        output (Path): Output directory for ICS files.
        tv_from (str): Source for TV info: 'auto', 'club_ics', or 'overrides'.
        overrides (Optional[Path]): Overrides YAML file path.
        club_ics_map (Path): Club ICS URLs mapping YAML file path.
        refresh_cache (bool): Whether to refresh the local team cache from the API.
        refresh_competitions (bool): Whether to refresh the local competitions cache from the API.
    """
    output.mkdir(parents=True, exist_ok=True)
    comps = [c.strip() for c in competitions.split(",") if c.strip()] if competitions else []

    client = FDClient()
    if refresh_cache:
        client.refresh_team_cache()

    if all_teams:
        teams: list[str] = []
        logger.warning("All teams feature not yet implemented")
    else:
        if not team:
            logger.error("Either --team or --all-teams must be specified.")
            raise typer.BadParameter("Provide --team or --all-teams")
        teams = [team]

    for t in teams:
        try:
            fixtures = client.fetch_fixtures(t, comps, season)
            fixtures = Filter.apply_filters(fixtures, scheduled_only=True)

            clubics_url = (
                _club_ics_url(t, club_ics_map) if tv_from in ("auto", "club_ics") else None
            )

            snap_path = Path("data/cache") / f"{_slug(t)}.{_slug(competitions or 'all')}.json"
            prev = load_snapshot(snap_path)

            stats = enrich_all(fixtures, overrides_path=overrides, club_ics_url=clubics_url)

            if home_only:
                fixtures = Filter.only_home(fixtures)
            if away_only:
                fixtures = Filter.only_away(fixtures)
            if televised_only:
                fixtures = Filter.only_televised(fixtures)

            comp_slug = _slug(competitions) if competitions else "all"
            fname = f"{_slug(t)}.{comp_slug}.ics"
            writer = ICSWriter(fixtures)
            writer.write(output / fname)
            logger.info(f"Wrote {len(fixtures)} fixtures for team '{t}' to {output / fname}")
            typer.echo(f"Wrote {len(fixtures)} fixtures for team '{t}' to {output / fname}")

            if summarise:
                changes = diff_changes(fixtures, prev)
                typer.echo(
                    f"[{t}] fixtures: {len(fixtures)}\n"
                    f"🔄 Changes since last update: {changes['time']} time, {changes['venue']} venue, {changes['status']} status\n"
                    f"📺 TV info added: {stats['tv_overrides_applied']}"
                )

            save_snapshot(fixtures, snap_path)

        except Exception as e:
            logger.error(f"Failed to build ICS for team '{t}': {e}")
            typer.echo(f"Failed to build ICS for team '{t}': {e}", err=True)


@app.command()
def cache_teams(
    competitions: str = typer.Option(
        ...,
        help="Comma-separated competition codes to cache teams for",
    ),
    output: Path = typer.Option(Path("data/teams.yaml"), help="Path to cache the team data"),
) -> None:
    """Cache team data for specified competitions.

    Args:
        competitions (str): Comma-separated competition codes.
        output (Path): Path to cache the team data.
    """
    client = FDClient()
    comps = [c.strip() for c in competitions.split(",") if c.strip()]
    client.refresh_team_cache(comps, cache_path=output)
    typer.echo(f"✅ Cached teams to {output}")


if __name__ == "__main__":
    app()
