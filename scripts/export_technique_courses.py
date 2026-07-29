#!/usr/bin/env python3
"""Validate canonical coach courses and export the public Pages artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from badminton_coach_skill.technique_courses import (
    public_technique_course_catalog_is_current,
    write_public_technique_course_catalog,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="BadmintonCoachSkill repository root",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and fail when committed public artifacts are stale",
    )
    args = parser.parse_args()
    if args.check:
        if not public_technique_course_catalog_is_current(args.root):
            raise SystemExit("public technique-course artifacts are stale")
        print("public technique-course artifacts are valid and current")
        return
    for path in write_public_technique_course_catalog(args.root):
        print(path)


if __name__ == "__main__":
    main()
