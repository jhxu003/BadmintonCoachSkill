from pathlib import Path
import csv
import json
import sys

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_source_index_has_required_header_and_no_private_paths():
    index = ROOT / "data" / "source-index.tsv"
    required = [
        "source_id",
        "title",
        "platform",
        "url",
        "published_at",
        "access_type",
        "authorization_status",
        "source_type",
        "topic_tags",
        "stroke_tags",
        "timestamps",
        "usability",
        "confidence",
        "notes",
    ]
    with index.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert reader.fieldnames == required
        rows = list(reader)

    assert rows, "source index should start with seed public sources"
    assert all("raw-private" not in row["url"] for row in rows)
    assert any(row["authorization_status"] in {"official", "authorized"} for row in rows)


def test_json_schemas_accept_minimal_valid_payloads():
    schemas = {
        name: json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        for name in [
            "player-profile.schema.json",
            "video-observation.schema.json",
            "diagnosis.schema.json",
        ]
    }
    profile = {
        "level": "beginner",
        "age_band": "adult",
        "strength": "average",
        "mobility": "normal",
        "coordination": "arm_dominant",
        "injury_risk": [],
        "training_goal": "clear_to_baseline",
        "dominant_hand": "right",
        "available_training_time": "20min_per_day",
    }
    observation = {
        "action": "high_clear",
        "camera_view": "rear_side",
        "fps_quality": "good",
        "phase_observations": {},
        "contact_point": "behind_head",
        "elbow_height_before_hit": "below_shoulder",
        "wrist_elbow_sequence": "wrist_before_elbow",
        "hip_shoulder_sequence": "late_hip",
        "racket_side_structure": "collapsed",
        "follow_through": "short",
        "footwork_observations": {"arrival_timing": "late", "recovery": "slow"},
        "missing_observations": [],
        "keyframes": [{"label": "pre_hit", "time_ms": 1840}],
    }
    diagnosis = {
        "primary_framework": "stable-overhead-frame",
        "issues": [],
        "evidence": [],
        "confidence": "medium",
        "priority_order": [],
        "training_plan": [],
        "retest_metrics": [],
        "missing_evidence": [],
        "safety_notes": [],
    }

    jsonschema.validate(profile, schemas["player-profile.schema.json"])
    jsonschema.validate(observation, schemas["video-observation.schema.json"])
    jsonschema.validate(diagnosis, schemas["diagnosis.schema.json"])


def test_rubric_rules_are_source_backed_or_marked_hypothesis():
    reference_dir = ROOT / "skills" / "liu-hui-badminton-coach" / "references"
    for filename in ["overhead-rubric.yaml", "footwork-rubric.yaml"]:
        rules = yaml.safe_load((reference_dir / filename).read_text(encoding="utf-8"))
        assert rules
        for rule in rules:
            assert rule["rule_id"]
            assert rule["observable_evidence"]
            assert rule["insufficient_evidence_policy"]
            assert rule["drills"]
            assert rule["retest_metrics"]
            assert rule["confidence"] in {"source_backed", "inferred", "hypothesis"}
            if rule["confidence"] == "source_backed":
                assert rule["source_ids"]


def test_skill_and_report_contract_contain_safety_boundaries():
    skill = (ROOT / "skills" / "liu-hui-badminton-coach" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    contract = (
        ROOT
        / "skills"
        / "liu-hui-badminton-coach"
        / "references"
        / "report-contract.md"
    ).read_text(encoding="utf-8")

    for phrase in ["非官方", "证据不足", "不模仿", "不声称"]:
        assert phrase in skill + contract
