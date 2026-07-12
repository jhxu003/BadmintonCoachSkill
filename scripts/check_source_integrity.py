from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.source_index import read_source_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate source references for one coach Skill.")
    parser.add_argument("--coach-config", default="configs/coaches/liu-hui.yaml")
    return parser.parse_args()


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _taxonomy_ids(taxonomy: dict[str, list[dict[str, object]]]) -> dict[str, set[str]]:
    return {
        section: {str(item["id"]) for item in items}
        for section, items in taxonomy.items()
    }


def _item_id(item: dict[str, object]) -> str:
    id_fields = [
        "framework_id",
        "rule_id",
        "profile_id",
        "stroke_id",
        "plan_id",
        "drill_id",
        "system_id",
    ]
    for field in id_fields:
        if field in item:
            return str(item[field])
    return "unknown"


def _collect_source_ids_from_node(
    node: object,
    *,
    owner: str,
) -> list[tuple[str, str]]:
    collected: list[tuple[str, str]] = []
    if isinstance(node, dict):
        item_id = _item_id(node)
        source_ids = node.get("source_ids")
        if isinstance(source_ids, list):
            for source_id in source_ids:
                collected.append((f"{owner}:{item_id}", str(source_id)))
        for child in node.values():
            collected.extend(_collect_source_ids_from_node(child, owner=owner))
    elif isinstance(node, list):
        for child in node:
            collected.extend(_collect_source_ids_from_node(child, owner=owner))
    return collected


def _collect_rule_source_ids(reference_dir: Path) -> list[tuple[str, str]]:
    collected: list[tuple[str, str]] = []
    for path in sorted(reference_dir.glob("*.yaml")):
        collected.extend(
            _collect_source_ids_from_node(_load_yaml(path), owner=path.name)
        )
    return collected


def main() -> None:
    args = parse_args()
    config = _load_yaml(ROOT / args.coach_config)
    source_index_path = ROOT / str(config["source_index"])
    corpus_path = ROOT / str(config["corpus_path"])
    reference_dir = ROOT / str(config["reference_path"])
    source_ids = {
        row["source_id"] for row in read_source_index(source_index_path)
    }
    taxonomy = _load_yaml(corpus_path / "system-taxonomy.yaml")
    taxonomy_ids = _taxonomy_ids(taxonomy)
    teaching_points = _load_yaml(corpus_path / "teaching-points.yaml")
    topic_map = _load_yaml(corpus_path / "source-topic-map.yaml")
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
