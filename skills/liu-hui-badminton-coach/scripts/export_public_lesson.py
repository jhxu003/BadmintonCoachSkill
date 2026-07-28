#!/usr/bin/env python3
"""Compatibility launcher for the repository-wide public lesson exporter."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[3] / "scripts" / "export_public_lesson.py"),
        run_name="__main__",
    )
