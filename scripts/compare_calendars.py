"""Script to comapare two calendar directories for changes"""

import os
from pathlib import Path

from src.logic.calendar.compare import CalendarComparison

if __name__ == "__main__":
    old_dir = Path("public-old")
    new_dir = Path("public")

    has_changes = CalendarComparison().compare_calendars(old_dir, new_dir)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as f:
            f.write(f"has_changes={'true' if has_changes else 'false'}\n")
    if has_changes:
        print("Calendars have changes")
    else:
        print("No changes in calendars")
