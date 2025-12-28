"""Build script for generating fixture calendars"""

from pathlib import Path
import sys

from src.app.cli import build

if __name__ == "__main__":
    result = build(
        team="Manchester United FC",
        competitions=["PL"],
        output=Path("public/calendars"),
    )

    if result["successful"]:
        print(f"\n✅ Built {len(result['successful'])} calendar(s)")
        for team, file_path in result["successful"]:
            print(f"   - {team}: {file_path}")

        if result["failed"]:
            print(f"\n⚠️  Failed to build {len(result['failed'])} calendar(s):")
            for team, error in result["failed"]:
                print(f"   - {team}: {error}")

        # Exit success if any succeeded (allows partial deployment)
        sys.exit(0)
    else:
        print("\n❌ Failed to build any calendars")
        sys.exit(1)
