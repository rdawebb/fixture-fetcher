"""Build script for generating fixture calendars."""

from pathlib import Path

from src.app.cli import build

if __name__ == "__main__":
    build(
        team="Manchester United FC",
        competitions="PL",
        output=Path("public/calendars"),
    )
