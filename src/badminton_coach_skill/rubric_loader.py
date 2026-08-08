from __future__ import annotations

import json
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


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _load_optional_json_mapping(path: Path) -> dict[str, Any]:
    """Load the public source-topic retrieval index when it is installed."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if data.get("schema_version") != "coach-skill-source-topic-index/v1":
        raise ValueError(f"{path} has an unsupported source-topic index schema")
    if not isinstance(data.get("sources"), list):
        raise ValueError(f"{path} must contain a sources list")
    return data


def load_skill_knowledge(reference_dir: str | Path) -> dict[str, Any]:
    """Load the skill's deterministic knowledge files."""
    root = Path(reference_dir)
    drills = _load_yaml(root / "drills.yaml")
    drill_map = {drill["drill_id"]: drill for drill in drills}
    rules: list[dict[str, Any]] = []
    for path in sorted(root.glob("*-rubric.yaml")):
        rules.extend(_load_yaml(path))

    return {
        "frameworks": _load_yaml(root / "frameworks.yaml"),
        "rules": rules,
        "drills": drills,
        "drill_map": drill_map,
        "multimodal_evidence": _load_mapping(root / "multimodal-evidence-map.yaml"),
        # Public title routes help a caller find the appropriate coaching
        # system.  They stay distinct from the evidence map because they do
        # not certify clips, frames, or deterministic rules.
        "source_topic_index": _load_optional_json_mapping(root / "source-topic-index.json"),
    }
