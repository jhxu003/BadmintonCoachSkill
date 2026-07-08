from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.issue_matcher import match_diagnosis
from badminton_coach_skill.rubric_loader import load_skill_knowledge


CASES = [
    ("high_clear", "high_clear_late_arrival.json"),
    ("smash", "smash_low_elbow.json"),
    ("rear_footwork", "rear_footwork_late_arrival.json"),
    ("front_footwork", "front_footwork_late_arrival.json"),
    ("backhand", "backhand_low_contact.json"),
    ("serve_receive", "serve_receive_large_preparation.json"),
    ("doubles", "doubles_watch_after_hit.json"),
]


def main() -> None:
    knowledge = load_skill_knowledge(
        ROOT / "skills" / "liu-hui-badminton-coach" / "references"
    )
    for label, filename in CASES:
        payload = json.loads(
            (ROOT / "examples" / "observations" / filename).read_text(
                encoding="utf-8"
            )
        )
        diagnosis = match_diagnosis(
            payload["player_profile"], payload["video_observation"], knowledge
        )
        top_issue = diagnosis["issues"][0]["issue_id"] if diagnosis["issues"] else "none"
        print(f"{label}: {top_issue}")


if __name__ == "__main__":
    main()
