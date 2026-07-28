"""Build script for generating fixture calendars"""

import argparse
import os
import sys
from pathlib import Path

import yaml

from app.cli import build, cache_teams
from backend.config import get_config
from utils.manifest import generate_manifest, load_color_overrides

config = get_config()
CACHE_PATH = config.get("CACHE_PATH", Path("data/cache/teams.yaml"))
TEAM_COLORS_PATH = Path(
    config.get("TEAM_COLORS_PATH", "data/overrides/team_colors.yaml")
)
FD_COMPETITIONS = config.get("FD_COMPETITIONS", {"PL": "Premier League"})


def refresh_team_cache() -> None:
    """Refresh the cached team list from the API.

    Runs before the team list is read so promotions/relegations are picked up.
    A failure here is not fatal: the build falls back to the existing cache.
    """
    print("🔄 Refreshing team cache...")
    try:
        cache_teams(list(FD_COMPETITIONS.keys()))

    except Exception as e:  # noqa: BLE001 - stale teams beat no build at all
        print(f"⚠️  Could not refresh team cache, falling back to cached teams: {e}")


def load_team_cache(cache_path: Path) -> dict:
    """Load the whole team cache, keyed by league then team name.

    Args:
        cache_path: Path to the cache file.

    Returns:
        Parsed cache contents, including each team's colours and crest.
    """
    try:
        with open(cache_path) as f:
            return yaml.safe_load(f) or {}

    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"❌ Error loading cache file: {e}")
        sys.exit(1)


def load_pl_teams(teams_data: dict) -> list[str]:
    """Pull the Premier League team names out of the cache.

    Args:
        teams_data: Parsed cache contents from load_team_cache.

    Returns:
        List of Premier League team names.
    """
    pl_teams = teams_data.get("Premier League", [])
    if not pl_teams:
        print("❌ No Premier League teams found in cache")
        sys.exit(1)

    return list(pl_teams.keys())


def build_calendars(teams: list[str], team_cache: dict | None = None):
    """Build calendar files for the specified teams and competitions.

    Args:
        teams: List of team names to build calendars for.
        team_cache: Parsed team cache, used to add names, colours and crests to
            the manifest.
    """
    calendars_dir = Path("public/calendars")

    result = build(
        teams=teams,
        competitions=["PL"],
        output=calendars_dir,
    )

    if result["successful"]:
        print(f"\n✅ Built {len(result['successful'])} calendar(s)")
        for team, file_path in result["successful"]:
            print(f"   - {team}: {file_path}")

        if result["failed"]:
            print(f"\n⚠️  Failed to build {len(result['failed'])} calendar(s):")
            for team, error in result["failed"]:
                print(f"   - {team}: {error}")

        print("\n📋 Generating calendar manifest...")
        try:
            generate_manifest(
                calendars_dir=calendars_dir,
                output_file=Path("public/calendars.json"),
                team_cache=team_cache,
                color_overrides=load_color_overrides(TEAM_COLORS_PATH),
            )
            print("✅ Calendar manifest generated successfully")

        except Exception as e:  # noqa: BLE001 - manifest failure must not fail the build
            print(f"⚠️  Failed to generate manifest: {e}")
            # Don't fail the build if manifest generation fails
            sys.exit(0)

        # Exit success if any succeeded (allows partial deployment)
        sys.exit(0)

    elif not result["failed"]:
        print(
            "\n⏸️ No upcoming fixtures found - off-season or schedule not yet published"
        )
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write("no_fixtures=true\n")

        sys.exit(0)

    else:
        print("\n❌ Failed to build any calendars")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build fixture calendars")
    parser.add_argument(
        "teams", nargs="*", help="Specific teams to build calendars for"
    )

    args = parser.parse_args()

    if not args.teams:
        refresh_team_cache()

    team_cache = load_team_cache(CACHE_PATH)
    teams_to_build = args.teams if args.teams else load_pl_teams(team_cache)

    build_calendars(teams_to_build, team_cache)
