"""Build script for generating fixture calendars."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.app.cli import build  # noqa: E402

if __name__ == "__main__":
    build(
        team="Manchester United FC",
        competitions="PL",
        output=Path("public"),
    )
