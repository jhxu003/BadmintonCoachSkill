from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_timestamp_review_covers_all_pending_teaching_points():
    teaching_points = yaml.safe_load(
        (ROOT / "data" / "corpus" / "teaching-points.yaml").read_text(
            encoding="utf-8"
        )
    )
    timestamp_review = yaml.safe_load(
        (ROOT / "data" / "corpus" / "timestamp-review.yaml").read_text(
            encoding="utf-8"
        )
    )

    pending_ids = {
        point["point_id"]
        for point in teaching_points
        if point["status"] == "needs_timestamp_review"
    }
    reviewed_ids = {
        review["point_id"] for review in timestamp_review["teaching_point_reviews"]
    }

    assert len(pending_ids) == 21
    assert pending_ids == reviewed_ids


def test_core_video_notes_are_not_overstated_as_internal_timestamps():
    timestamp_review = yaml.safe_load(
        (ROOT / "data" / "corpus" / "timestamp-review.yaml").read_text(
            encoding="utf-8"
        )
    )
    notes = timestamp_review["core_video_timestamp_notes"]

    assert len(notes) >= 9
    assert all(note["timestamp_scope"] == "whole_clip_title_backed" for note in notes)
    assert all(note["segments"] for note in notes)
    assert all("no public subtitle track" in note["segments"][0]["note"] for note in notes)


def test_reviewed_corpus_rules_are_loaded_by_skill():
    skill = (ROOT / "skills" / "liu-hui-badminton-coach" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    rules = yaml.safe_load(
        (
            ROOT
            / "skills"
            / "liu-hui-badminton-coach"
            / "references"
            / "reviewed-corpus-rules.yaml"
        ).read_text(encoding="utf-8")
    )

    assert "references/reviewed-corpus-rules.yaml" in skill
    assert len(rules) == 21
    assert all(rule["decision"] for rule in rules)
    assert any(rule["decision"] == "reviewed_not_promoted" for rule in rules)
