from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.issue_matcher import match_diagnosis
from badminton_coach_skill.rubric_loader import load_skill_knowledge


REFERENCES = ROOT / "skills" / "liu-hui-badminton-coach" / "references"


def _profile(training_goal: str) -> dict[str, object]:
    return {
        "level": "intermediate",
        "age_band": "adult",
        "strength": "average",
        "mobility": "normal",
        "coordination": "balanced",
        "injury_risk": [],
        "training_goal": training_goal,
        "dominant_hand": "right",
        "available_training_time": "20min_per_day",
    }


def _observation(action: str, phase_observations: dict[str, object]) -> dict[str, object]:
    return {
        "action": action,
        "camera_view": "rear_side",
        "fps_quality": "good",
        "phase_observations": phase_observations,
        "contact_point": "front_high",
        "elbow_height_before_hit": "near_shoulder",
        "wrist_elbow_sequence": "elbow_before_wrist",
        "hip_shoulder_sequence": "hip_before_arm",
        "racket_side_structure": "stable",
        "follow_through": "complete",
        "footwork_observations": {"arrival_timing": "on_time", "recovery": "normal"},
        "missing_observations": [],
        "keyframes": [{"label": "contact", "time_ms": 1200}],
    }


def test_drop_frame_emits_drop_specific_issue_and_drill():
    knowledge = load_skill_knowledge(REFERENCES)
    diagnosis = match_diagnosis(
        _profile("light_drop"),
        _observation(
            "drop",
            {
                "shot_intent": "light_drop",
                "drop_speed": "slow_high",
                "disguise": "early_reveal",
            },
        ),
        knowledge,
    )

    assert diagnosis["primary_framework"] == "light-drop-frame"
    issue_ids = [issue["issue_id"] for issue in diagnosis["issues"]]
    assert "drop-too-slow" in issue_ids
    assert diagnosis["training_plan"]


def test_body_jammed_drive_emits_spacing_and_compactness_issue():
    knowledge = load_skill_knowledge(REFERENCES)
    diagnosis = match_diagnosis(
        _profile("body_jammed_drive"),
        _observation(
            "drive",
            {
                "pressure_state": "body_jammed",
                "preparation_size": "large",
                "spacing": "too_close",
            },
        ),
        knowledge,
    )

    assert diagnosis["primary_framework"] == "body-jammed-drive-frame"
    issue_ids = [issue["issue_id"] for issue in diagnosis["issues"]]
    assert "body-jammed-spacing" in issue_ids
    assert "drive-large-preparation" in issue_ids


def test_match_transfer_breakdown_is_a_first_class_issue():
    knowledge = load_skill_knowledge(REFERENCES)
    diagnosis = match_diagnosis(
        _profile("match_transfer"),
        _observation("smash", {"drill_form_ok_rally_breaks": True}),
        knowledge,
    )

    assert diagnosis["primary_framework"] == "match-transfer-frame"
    issue_ids = [issue["issue_id"] for issue in diagnosis["issues"]]
    assert "drill-form-rally-breakdown" in issue_ids
