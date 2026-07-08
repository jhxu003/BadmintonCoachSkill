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
        "keyframes": [{"label": "contact", "time_ms": 1000}],
    }


def test_equipment_fit_has_runtime_issue_not_only_source_metadata():
    knowledge = load_skill_knowledge(REFERENCES)
    diagnosis = match_diagnosis(
        _profile("racket_weight_fit"),
        _observation("high_clear", {"racket_weight_fit": "too_heavy_for_stage"}),
        knowledge,
    )

    assert diagnosis["primary_framework"] == "equipment-fit-frame"
    assert "racket-too-heavy-for-stage" in [
        issue["issue_id"] for issue in diagnosis["issues"]
    ]


def test_big_arm_correction_has_runtime_issue():
    knowledge = load_skill_knowledge(REFERENCES)
    diagnosis = match_diagnosis(
        _profile("big_arm_correction"),
        _observation("smash", {"arm_path": "big_arm_pull"}),
        knowledge,
    )

    assert diagnosis["primary_framework"] == "arm-path-correction-frame"
    assert "big-arm-dominant-swing" in [
        issue["issue_id"] for issue in diagnosis["issues"]
    ]


def test_deceleration_release_has_runtime_issue():
    knowledge = load_skill_knowledge(REFERENCES)
    diagnosis = match_diagnosis(
        _profile("deceleration_release"),
        _observation("smash", {"deceleration": "forced_stop"}),
        knowledge,
    )

    assert diagnosis["primary_framework"] == "deceleration-release-frame"
    assert "deceleration-missing" in [
        issue["issue_id"] for issue in diagnosis["issues"]
    ]


def test_jump_smash_framework_has_runtime_issues():
    knowledge = load_skill_knowledge(REFERENCES)
    diagnosis = match_diagnosis(
        _profile("jump_smash"),
        _observation(
            "smash",
            {
                "shot_intent": "jump_smash",
                "jump_contact": "missed_window",
                "landing_recovery": "unstable",
            },
        ),
        knowledge,
    )

    assert diagnosis["primary_framework"] == "jump-smash-airtime-frame"
    issue_ids = [issue["issue_id"] for issue in diagnosis["issues"]]
    assert "jump-contact-window-missed" in issue_ids
    assert "jump-landing-recovery-unstable" in issue_ids
