"""Script to compare static files for changes"""

import os
from pathlib import Path
from filecmp import dircmp


def compare_directories(old_dir: Path | None, new_dir: Path | None) -> bool:
    """
    Compare two directories recursively.

    Args:
        old_dir: The old directory to compare.
        new_dir: The new directory to compare.

    Returns:
        True if there are differences, False if identical.
    """
    if old_dir is None and new_dir is None:
        return False

    if (
        old_dir is None
        or new_dir is None
        or not old_dir.exists()
        or not new_dir.exists()
    ):
        return True

    dcmp = dircmp(str(old_dir), str(new_dir))

    # If there are any differences in files or subdirectories
    if dcmp.left_only or dcmp.right_only or dcmp.diff_files:
        return True

    # Recursively check subdirectories
    for common_dir in dcmp.common_dirs:
        if old_dir is not None and new_dir is not None:
            if compare_directories(old_dir / common_dir, new_dir / common_dir):
                return True

    return False


if __name__ == "__main__":
    old_dir = Path("public-old")
    new_dir = Path("public")

    # Check static files
    static_changed = False

    if old_dir.exists() and new_dir.exists():
        dcmp = dircmp(str(old_dir), str(new_dir))
        if dcmp.left_only or dcmp.right_only:
            non_calendar_diff = any(
                name != "calendars" and name != "calendars.json"
                for name in dcmp.left_only + dcmp.right_only
            )
            static_changed = non_calendar_diff

        if dcmp.diff_files:
            non_calendar_diff_files = [
                name for name in dcmp.diff_files if name != "calendars.json"
            ]
            if non_calendar_diff_files:
                static_changed = True

        # Recursively check subdirectories (excluding calendars)
        for common_dir in dcmp.common_dirs:
            if common_dir != "calendars":
                old_subdir = old_dir / common_dir
                new_subdir = new_dir / common_dir
                if compare_directories(old_subdir, new_subdir):
                    static_changed = True
                    break
    else:
        static_changed = True

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as f:
            f.write(f"static_changed={'true' if static_changed else 'false'}\n")

    if static_changed:
        print("Static files have changes")
    else:
        print("No changes in static files")
