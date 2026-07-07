from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.issue_matcher import match_diagnosis
from badminton_coach_skill.rubric_loader import load_skill_knowledge


REFERENCES = ROOT / "skills" / "liu-hui-badminton-coach" / "references"


def test_late_arrival_is_prioritized_before_hand_technique():
    knowledge = load_skill_knowledge(REFERENCES)
    profile = {
        "level": "beginner",
        "age_band": "adult",
        "strength": "average",
        "mobility": "limited",
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

    diagnosis = match_diagnosis(profile, observation, knowledge)

    assert diagnosis["primary_framework"] == "stable-overhead-frame"
    assert diagnosis["issues"][0]["issue_id"] == "late-arrival"
    assert [issue["issue_id"] for issue in diagnosis["issues"][:3]] == [
        "late-arrival",
        "contact-point-behind",
        "low-elbow",
    ]
    assert diagnosis["issues"][0]["evidence"]
    assert diagnosis["issues"][0]["source_ids"]


def test_missing_hip_sequence_prevents_definitive_hip_rotation_diagnosis():
    knowledge = load_skill_knowledge(REFERENCES)
    profile = {
        "level": "intermediate",
        "age_band": "adult",
        "strength": "good",
        "mobility": "normal",
        "coordination": "balanced",
        "injury_risk": [],
        "training_goal": "smash_power",
        "dominant_hand": "right",
        "available_training_time": "30min_per_day",
    }
    observation = {
        "action": "smash",
        "camera_view": "rear_side",
        "fps_quality": "good",
        "phase_observations": {},
        "contact_point": "front_high",
        "elbow_height_before_hit": "near_shoulder",
        "wrist_elbow_sequence": "elbow_before_wrist",
        "hip_shoulder_sequence": "missing",
        "racket_side_structure": "stable",
        "follow_through": "complete",
        "footwork_observations": {"arrival_timing": "on_time", "recovery": "normal"},
        "missing_observations": ["hip_shoulder_sequence"],
        "keyframes": [{"label": "contact", "time_ms": 2200}],
    }

    diagnosis = match_diagnosis(profile, observation, knowledge)

    issue_ids = [issue["issue_id"] for issue in diagnosis["issues"]]
    assert "late-hip-rotation" not in issue_ids
    assert "hip_shoulder_sequence" in diagnosis["missing_evidence"]


def test_low_elbow_and_behind_contact_emit_retest_metrics_and_drill():
    knowledge = load_skill_knowledge(REFERENCES)
    profile = {
        "level": "beginner",
        "age_band": "adult",
        "strength": "average",
        "mobility": "normal",
        "coordination": "arm_dominant",
        "injury_risk": ["shoulder_discomfort"],
        "training_goal": "clear_to_baseline",
        "dominant_hand": "right",
        "available_training_time": "15min_per_day",
    }
    observation = {
        "action": "high_clear",
        "camera_view": "side",
        "fps_quality": "good",
        "phase_observations": {},
        "contact_point": "behind_head",
        "elbow_height_before_hit": "below_shoulder",
        "wrist_elbow_sequence": "wrist_before_elbow",
        "hip_shoulder_sequence": "late_hip",
        "racket_side_structure": "collapsed",
        "follow_through": "short",
        "footwork_observations": {"arrival_timing": "on_time", "recovery": "normal"},
        "missing_observations": [],
        "keyframes": [{"label": "pre_hit", "time_ms": 1530}],
    }

    diagnosis = match_diagnosis(profile, observation, knowledge)
    issues = {issue["issue_id"]: issue for issue in diagnosis["issues"]}

    assert "low-elbow" in issues
    assert "contact-point-behind" in issues
    assert issues["low-elbow"]["drills"]
    assert issues["contact-point-behind"]["retest_metrics"]
    assert diagnosis["safety_notes"]
