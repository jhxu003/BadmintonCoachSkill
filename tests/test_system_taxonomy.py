from pathlib import Path
import json

import jsonschema
import yaml

from badminton_coach_skill.taxonomy import load_system_taxonomy


ROOT = Path(__file__).resolve().parents[1]


def test_system_taxonomy_covers_complete_coaching_surface():
    schema = json.loads(
        (ROOT / "schemas" / "system-taxonomy.schema.json").read_text(
            encoding="utf-8"
        )
    )
    taxonomy = yaml.safe_load(
        (ROOT / "data" / "corpus" / "system-taxonomy.yaml").read_text(
            encoding="utf-8"
        )
    )

    jsonschema.validate(taxonomy, schema)
    required_sections = {
        "student_profiles",
        "power_frameworks",
        "stroke_families",
        "footwork_families",
        "correction_order",
        "drill_families",
        "training_plans",
        "match_transfer",
    }
    assert required_sections.issubset(taxonomy)

    stroke_ids = {item["id"] for item in taxonomy["stroke_families"]}
    for required in [
        "high_clear",
        "smash",
        "drop",
        "drive",
        "net",
        "backhand",
        "serve_receive",
        "doubles",
    ]:
        assert required in stroke_ids

    framework_ids = {item["id"] for item in taxonomy["power_frameworks"]}
    for required in [
        "stable_overhead_frame",
        "kinetic_chain_power",
        "compact_frontcourt",
        "late_arrival_recovery",
        "equipment_fit",
        "arm_path_correction",
        "deceleration_release",
        "jump_smash_specialization",
        "smash_variants",
        "overhead_variation",
        "student_fit_power_selection",
    ]:
        assert required in framework_ids


def test_load_system_taxonomy_returns_sections():
    taxonomy = load_system_taxonomy(ROOT / "data" / "corpus" / "system-taxonomy.yaml")

    assert "student_profiles" in taxonomy
    assert "stroke_families" in taxonomy
