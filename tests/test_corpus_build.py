from pathlib import Path
import subprocess
import sys

import json
import jsonschema
import yaml

from badminton_coach_skill.source_index import read_source_index, summarize_source_index


ROOT = Path(__file__).resolve().parents[1]


def test_source_index_is_expanded_into_a_real_corpus_seed():
    rows = read_source_index(ROOT / "data" / "source-index.tsv")

    assert len(rows) >= 30
    assert any(
        row["platform"] == "YouTube"
        and row["authorization_status"] == "official"
        and row["source_type"] == "channel"
        for row in rows
    )
    assert any(
        row["platform"] == "Bilibili"
        and row["authorization_status"] == "authorized"
        for row in rows
    )
    assert any(row["platform"] == "Douyin" for row in rows)
    assert any(row["source_type"] == "discussion" for row in rows)
    assert any("high_clear" in row["stroke_tags"] for row in rows)
    assert any("smash" in row["stroke_tags"] for row in rows)
    assert any("footwork" in row["stroke_tags"] for row in rows)


def test_corpus_summary_reports_coverage_by_platform_and_status():
    rows = read_source_index(ROOT / "data" / "source-index.tsv")
    summary = summarize_source_index(rows)

    assert summary["total_sources"] >= 30
    assert summary["by_platform"]["YouTube"] >= 5
    assert summary["by_platform"]["Bilibili"] >= 10
    assert summary["by_authorization_status"]["official"] >= 1
    assert summary["by_authorization_status"]["authorized"] >= 1
    assert summary["by_usability"]["usable"] >= 10


def test_teaching_points_are_traceable_to_source_index():
    rows = read_source_index(ROOT / "data" / "source-index.tsv")
    source_ids = {row["source_id"] for row in rows}
    schema = json.loads(
        (ROOT / "schemas" / "teaching-point.schema.json").read_text(encoding="utf-8")
    )
    teaching_points = yaml.safe_load(
        (ROOT / "data" / "corpus" / "teaching-points.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert len(teaching_points) >= 10
    for point in teaching_points:
        jsonschema.validate(point, schema)
        assert point["point_id"]
        assert point["summary"]
        assert point["evidence_type"] in {
            "source_title",
            "timestamp_note",
            "inferred_from_titles",
            "third_party",
        }
        assert point["status"] in {"ready_for_skill", "needs_timestamp_review"}
        assert point["source_ids"]
        assert set(point["source_ids"]).issubset(source_ids)
        if point["status"] == "ready_for_skill":
            assert point["usable_in_rules"] is True


def test_corpus_report_script_outputs_reproducible_summary():
    result = subprocess.run(
        [sys.executable, "scripts/build_corpus_report.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Corpus Build Report" in result.stdout
    assert "Total sources:" in result.stdout
    assert "Teaching points:" in result.stdout
    assert "Official/authorized/public separation:" in result.stdout
