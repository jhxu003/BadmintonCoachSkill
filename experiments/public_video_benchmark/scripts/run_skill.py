#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import BENCHMARK_ROOT, CONFIG_PATH, PROJECT_ROOT, ensure_import_path, load_json, load_yaml, write_json

ensure_import_path()
from badminton_coach_skill.coach_registry import load_coach_knowledge  # noqa: E402
from badminton_coach_skill.issue_matcher import match_diagnosis  # noqa: E402


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    parser = argparse.ArgumentParser(description="Route valid benchmark observations through the existing Skill.")
    parser.add_argument("--all", action="store_true", help="Process every configured observer result.")
    parser.add_argument("--model", choices=sorted(config["inference"]["models"]))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.all and not args.model:
        parser.error("use --all or --model")

    mapping = load_yaml(BENCHMARK_ROOT / "configs" / "action_mapping.yaml")
    coach_id = str(config["skill"]["coach_id"])
    knowledge = load_coach_knowledge(coach_id, PROJECT_ROOT)
    profile = dict(config["skill"]["player_profile"])
    models = list(config["inference"]["models"]) if args.all else [args.model]
    counts = {"success": 0, "unsupported_action": 0, "invalid_observation": 0}
    for model_name in models:
        model_config = config["inference"]["models"][model_name]
        root = BENCHMARK_ROOT / "results" / str(model_config["result_dir"])
        if not root.exists():
            continue
        for sample_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            output = sample_dir / "coach_result.json"
            if output.exists() and not args.force:
                continue
            meta_path = sample_dir / "run_meta.json"
            observation_path = sample_dir / "observation.json"
            if not meta_path.exists() or not observation_path.exists():
                counts["invalid_observation"] += 1
                write_json(output, {"status": "invalid_observation", "issues": [], "missing_evidence": []})
                continue
            meta = load_json(meta_path)
            dataset_action = str(meta.get("dataset_action", ""))
            route = mapping.get(dataset_action, {})
            skill_action = route.get("skill_action")
            if route.get("status") != "mapped" or not skill_action:
                counts["unsupported_action"] += 1
                write_json(output, {"status": "unsupported_action", "dataset_action": dataset_action, "issues": [], "missing_evidence": []})
                continue
            observation = load_json(observation_path)
            # The model remains responsible for recognition. Mapping only normalizes an equivalent label.
            if observation.get("action") == "unknown":
                counts["unsupported_action"] += 1
                write_json(output, {"status": "unsupported_action", "dataset_action": dataset_action, "issues": [], "missing_evidence": ["action"]})
                continue
            diagnosis = match_diagnosis(profile, observation, knowledge)
            diagnosis["status"] = "success"
            diagnosis["dataset_action"] = dataset_action
            diagnosis["expected_skill_action"] = skill_action
            write_json(output, diagnosis)
            counts["success"] += 1
    print(counts)


if __name__ == "__main__":
    main()
