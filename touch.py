#!/usr/bin/env python3
"""
touch.py - Updates BUILD_TIMESTAMP in ui/about_dialog.py with the current local timestamp.
Usage: Run right before 'git push'.
"""

import re
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    target_file = Path(__file__).parent / "ui" / "about_dialog.py"
    if not target_file.is_file():
        print(f"Error: Target file not found: {target_file}", file=sys.stderr)
        return 1

    # ISO 8601 local timestamp with timezone offset, e.g. 2026-11-01T19:55:00+02:00
    now_str = datetime.now().astimezone().isoformat(timespec="seconds")

    content = target_file.read_text(encoding="utf-8")
    new_content, count = re.subn(
        r'BUILD_TIMESTAMP\s*:\s*str\s*=\s*["\'][^"\']*["\']',
        f'BUILD_TIMESTAMP: str = "{now_str}"',
        content,
    )
    if count == 0:
        new_content, count = re.subn(
            r'BUILD_TIMESTAMP\s*=\s*["\'][^"\']*["\']',
            f'BUILD_TIMESTAMP = "{now_str}"',
            content,
        )

    if count > 0:
        target_file.write_text(new_content, encoding="utf-8")
        print(f"Updated BUILD_TIMESTAMP to \"{now_str}\" in ui/about_dialog.py")
        return 0
    else:
        print(f"Error: BUILD_TIMESTAMP variable not found in {target_file}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

