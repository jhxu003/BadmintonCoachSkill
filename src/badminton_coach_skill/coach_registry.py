from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .rubric_loader import load_skill_knowledge


def _config_dir(root: Path) -> Path:
    return root / "configs" / "coaches"


def available_coaches(root: str | Path) -> list[str]:
    return sorted(path.stem for path in _config_dir(Path(root)).glob("*.yaml"))


def load_coach_config(coach_id: str, root: str | Path) -> dict[str, Any]:
    project_root = Path(root)
    path = _config_dir(project_root) / f"{coach_id}.yaml"
    if not path.exists():
        choices = ", ".join(available_coaches(project_root))
        raise ValueError(f"Unknown coach_id {coach_id!r}. Available coaches: {choices}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("coach_id") != coach_id:
        raise ValueError(f"Invalid coach config: {path}")
    return data


def load_coach_knowledge(coach_id: str, root: str | Path) -> dict[str, Any]:
    project_root = Path(root)
    coach = load_coach_config(coach_id, project_root)
    knowledge = load_skill_knowledge(project_root / str(coach["reference_path"]))
    knowledge["coach"] = coach
    return knowledge

