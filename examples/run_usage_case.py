from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.issue_matcher import match_diagnosis
from badminton_coach_skill.report_compiler import compile_llm_context
from badminton_coach_skill.rubric_loader import load_skill_knowledge


def main() -> None:
    case_path = ROOT / "examples" / "observations" / "high_clear_late_arrival.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    knowledge = load_skill_knowledge(
        ROOT / "skills" / "liu-hui-badminton-coach" / "references"
    )
    diagnosis = match_diagnosis(
        payload["player_profile"], payload["video_observation"], knowledge
    )

    print(f"Primary framework: {diagnosis['primary_framework']}")
    if diagnosis["issues"]:
        top_issue = diagnosis["issues"][0]
        print(f"Top priority: {top_issue['issue_id']}")
        print("Evidence:")
        for evidence in top_issue["evidence"]:
            print(f"- {evidence}")
        if top_issue["drills"]:
            drill = top_issue["drills"][0]
            print(f"Drill: {drill['name']} - {drill['dosage']}")
    print()
    print("LLM context:")
    print(compile_llm_context(diagnosis))


if __name__ == "__main__":
    main()

