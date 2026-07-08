from __future__ import annotations

from pathlib import Path

import yaml


def load_system_taxonomy(path: str | Path) -> dict[str, list[dict[str, object]]]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
