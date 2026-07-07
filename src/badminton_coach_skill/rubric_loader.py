from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a YAML list")
    return data


def load_skill_knowledge(reference_dir: str | Path) -> dict[str, Any]:
    """Load the skill's deterministic knowledge files."""
    root = Path(reference_dir)
    drills = _load_yaml(root / "drills.yaml")
    drill_map = {drill["drill_id"]: drill for drill in drills}
    rules = _load_yaml(root / "footwork-rubric.yaml") + _load_yaml(
        root / "overhead-rubric.yaml"
    )

    return {
        "frameworks": _load_yaml(root / "frameworks.yaml"),
        "rules": rules,
        "drills": drills,
        "drill_map": drill_map,
    }

