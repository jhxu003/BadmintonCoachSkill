#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import BENCHMARK_ROOT, CONFIG_PATH, load_json, load_yaml
from run_observer import smoke_subset


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    parser = argparse.ArgumentParser(description="Enforce the documented >=10/12 smoke-test gate.")
    parser.add_argument("--model", choices=sorted(config["inference"]["models"]), required=True)
    parser.add_argument("--manifest", default="data/manifests/badminsense_60.json")
    args = parser.parse_args()
    rows = smoke_subset(load_json(BENCHMARK_ROOT / args.manifest))
    result_dir = BENCHMARK_ROOT / "results" / config["inference"]["models"][args.model]["result_dir"]
    successes = 0
    for row in rows:
        sample_dir = result_dir / row["sample_id"]
        meta = load_json(sample_dir / "run_meta.json") if (sample_dir / "run_meta.json").exists() else {}
        coach = load_json(sample_dir / "coach_result.json") if (sample_dir / "coach_result.json").exists() else {}
        if meta.get("schema_valid") and coach.get("status") == "success":
            successes += 1
    threshold = int(config["smoke"]["pass_threshold"])
    print(f"{args.model}: {successes}/{len(rows)} smoke pipelines succeeded (required {threshold})")
    if len(rows) != int(config["smoke"]["total"]) or successes < threshold:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
