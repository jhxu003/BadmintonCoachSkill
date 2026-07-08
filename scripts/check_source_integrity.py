from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.source_index import read_source_index


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _taxonomy_ids(taxonomy: dict[str, list[dict[str, object]]]) -> dict[str, set[str]]:
    return {
        section: {str(item["id"]) for item in items}
        for section, items in taxonomy.items()
    }


def _collect_rule_source_ids(reference_dir: Path) -> list[tuple[str, str]]:
    collected: list[tuple[str, str]] = []
    for filename in ["frameworks.yaml", "overhead-rubric.yaml", "footwork-rubric.yaml"]:
        path = reference_dir / filename
        for item in _load_yaml(path):
            item_id = str(item.get("framework_id") or item.get("rule_id") or "unknown")
            for source_id in item.get("source_ids", []):
                collected.append((f"{filename}:{item_id}", source_id))
    return collected


def main() -> None:
    source_ids = {
        row["source_id"] for row in read_source_index(ROOT / "data" / "source-index.tsv")
    }
    taxonomy = _load_yaml(ROOT / "data" / "corpus" / "system-taxonomy.yaml")
    taxonomy_ids = _taxonomy_ids(taxonomy)
    teaching_points = _load_yaml(ROOT / "data" / "corpus" / "teaching-points.yaml")
    topic_map = _load_yaml(ROOT / "data" / "corpus" / "source-topic-map.yaml")
    missing: list[str] = []

    for point in teaching_points:
        for source_id in point["source_ids"]:
            if source_id not in source_ids:
                missing.append(f"teaching-point:{point['point_id']}->{source_id}")

    for row in topic_map:
        source_id = row["source_id"]
        section = row["taxonomy_section"]
        if source_id not in source_ids:
            missing.append(f"source-topic-map:{source_id}")
        if section not in taxonomy_ids:
            missing.append(f"source-topic-map:{source_id}->missing-section:{section}")
            continue
        for taxonomy_id in row["taxonomy_ids"]:
            if taxonomy_id not in taxonomy_ids[section]:
                missing.append(
                    f"source-topic-map:{source_id}->{section}:{taxonomy_id}"
                )

    reference_dir = ROOT / "skills" / "liu-hui-badminton-coach" / "references"
    for owner, source_id in _collect_rule_source_ids(reference_dir):
        if source_id not in source_ids:
            missing.append(f"skill-rule:{owner}->{source_id}")

    if missing:
        print("source_integrity_failed")
        for item in missing:
            print(item)
        raise SystemExit(1)

    print("source_integrity_ok")


if __name__ == "__main__":
    main()
