"""Build script for generating fixture calendars"""

from pathlib import Path
import sys
import argparse
import yaml

from app.cli import build
from utils.manifest import generate_manifest
from backend.config import get_config

config = get_config()
CACHE_PATH = config.get("CACHE_PATH", Path("data/cache/teams.yaml"))


def load_pl_teams(cache_path: Path) -> list[str]:
    """Load Premier League teams from the cache file.

    Args:
        cache_path: Path to the cache file.

    Returns:
        List of Premier League team names.
    """
    try:
        with open(cache_path) as f:
            teams_data = yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"❌ Error loading cache file: {e}")
        sys.exit(1)

    pl_teams = teams_data.get("Premier League", [])
    if not pl_teams:
        print("❌ No Premier League teams found in cache")
        sys.exit(1)

    return list(pl_teams.keys())


def build_calendars(teams: list[str]):
    """Build calendar files for the specified teams and competitions.

    Args:
        teams: List of team names to build calendars for.
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
            )
            print("✅ Calendar manifest generated successfully")
        except Exception as e:
            print(f"⚠️  Failed to generate manifest: {e}")
            # Don't fail the build if manifest generation fails
            sys.exit(0)

        # Exit success if any succeeded (allows partial deployment)
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

    teams_to_build = args.teams if args.teams else load_pl_teams(CACHE_PATH)

    build_calendars(teams_to_build)
