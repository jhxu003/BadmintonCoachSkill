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


def available_coach_actions(coach_id: str, root: str | Path) -> list[str]:
    """Read only the small framework index for request-time action validation."""
    project_root = Path(root)
    coach = load_coach_config(coach_id, project_root)
    path = project_root / str(coach["reference_path"]) / "frameworks.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Invalid framework index: {path}")
    return sorted(
        {
            str(action)
            for framework in data
            if isinstance(framework, dict)
            for action in framework.get("applicable_actions", [])
            if action
        }
    )


def find_topic_teaching_units(
    coach_id: str,
    root: str | Path,
    *,
    topic_id: str | None = None,
    source_id: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve knowledge-only topic units without selecting any media.

    A caller may use a public title route to find a detailed coach-system
    unit.  Media remains absent until the private audit binds an exact
    reviewed source/topic asset, so this helper cannot cause cross-topic clip
    substitution.
    """
    if not topic_id and not source_id:
        raise ValueError("topic_id or source_id is required")
    units = load_coach_knowledge(coach_id, root).get("topic_teaching_units", {})
    if not isinstance(units, dict):
        return []
    results = [
        dict(unit)
        for unit in units.get("units", [])
        if isinstance(unit, dict)
        and (not topic_id or unit.get("topic_id") == topic_id)
        and (not source_id or source_id in unit.get("source_ids", []))
    ]
    return sorted(results, key=lambda unit: str(unit.get("topic_id", "")))
