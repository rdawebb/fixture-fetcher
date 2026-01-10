"""Build script for generating fixture calendars"""

from pathlib import Path
import sys

from app.cli import build
from utils.manifest import generate_manifest

if __name__ == "__main__":
    calendars_dir = Path("public/calendars")

    result = build(
        team="Manchester United FC",
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
