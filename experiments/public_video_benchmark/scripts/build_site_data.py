#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

from common import BENCHMARK_ROOT, CONFIG_PATH, PROJECT_ROOT, load_json, load_yaml, write_json


SITE_SOURCE = BENCHMARK_ROOT / "site"
PUBLIC_ROOT = PROJECT_ROOT / "web" / "public" / "benchmark"


def coach_view(coach: dict[str, Any]) -> dict[str, Any]:
    issues = coach.get("issues", []) if coach.get("status") == "success" else []
    primary = issues[0] if issues else {}
    plan = coach.get("training_plan", [])
    return {
        "status": coach.get("status", "not_run"),
        "primary_issue": primary.get("issue"),
        "issues": issues,
        "evidence": coach.get("evidence", []),
        "confidence": coach.get("confidence"),
        "why": primary.get("likely_effect", []),
        "correction": primary.get("correction_principle"),
        "drill": plan[0] if plan else None,
        "retest": coach.get("retest_metrics", []),
        "missing_evidence": coach.get("missing_evidence", []),
    }


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    parser = argparse.ArgumentParser(description="Build public-safe static benchmark data and copy exact source GIFs.")
    parser.add_argument("--manifest", default="data/manifests/badminsense_60.json")
    parser.add_argument("--no-media", action="store_true")
    args = parser.parse_args()
    manifest_path = BENCHMARK_ROOT / args.manifest
    if not manifest_path.exists():
        rows: list[dict[str, Any]] = []
    else:
        rows = load_json(manifest_path)
    metrics_path = BENCHMARK_ROOT / "results" / "summary" / "metrics.json"
    metrics = load_json(metrics_path) if metrics_path.exists() else {"dataset": "BADS_CLL", "manifest_samples": len(rows), "models": {}}

    PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
    for filename in ("index.html", "styles.css", "app.js"):
        shutil.copy2(SITE_SOURCE / filename, PUBLIC_ROOT / filename)
    media_root = PUBLIC_ROOT / "media"
    media_root.mkdir(exist_ok=True)
    raw_root = BENCHMARK_ROOT / "data" / "raw" / "BADS_CLL"
    cases = []
    for row in rows:
        sample_id = str(row["sample_id"])
        source_media = raw_root / str(row["media_path"])
        public_name = f"{sample_id}.gif".replace("/", "_")
        if not args.no_media and source_media.is_file():
            shutil.copy2(source_media, media_root / public_name)
        models: dict[str, Any] = {}
        for model_name, model_config in config["inference"]["models"].items():
            result_dir = BENCHMARK_ROOT / "results" / model_config["result_dir"] / sample_id
            meta = load_json(result_dir / "run_meta.json") if (result_dir / "run_meta.json").exists() else {}
            observation = load_json(result_dir / "observation.json") if (result_dir / "observation.json").exists() else None
            coach = load_json(result_dir / "coach_result.json") if (result_dir / "coach_result.json").exists() else {}
            models[model_name] = {
                "name": model_config["model_id"],
                "schema_valid": bool(meta.get("schema_valid")),
                "runtime_seconds": meta.get("runtime_seconds"),
                "observation": observation,
                "coach": coach_view(coach),
            }
        cases.append(
            {
                "sample_id": sample_id,
                "dataset": {
                    "name": "BADS_CLL",
                    "stroke_type": row["stroke_type"],
                    "quality_rating": row["quality_rating"],
                    "quality_tier": row["quality_tier"],
                    "experience": row.get("experience"),
                    "impact_location": row.get("impact_location"),
                    "media": f"media/{public_name}" if source_media.is_file() else None,
                },
                "models": models,
            }
        )
    write_json(PUBLIC_ROOT / "data" / "site_results.json", {"metrics": metrics, "cases": cases})
    print(f"Built {len(cases)} public benchmark cases -> {PUBLIC_ROOT}")


if __name__ == "__main__":
    main()
