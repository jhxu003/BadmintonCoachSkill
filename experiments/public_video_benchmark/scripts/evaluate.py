#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import BENCHMARK_ROOT, CONFIG_PATH, load_json, load_yaml, write_json


CONFIDENCE_WEIGHT = {"low": 0.25, "medium": 0.6, "high": 1.0, "hypothesis": 0.5}


def evaluate_model(model_name: str, result_dir: Path, manifest: dict[str, dict[str, Any]], mapping: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for sample_id, dataset in manifest.items():
        sample_dir = result_dir / sample_id
        meta = load_json(sample_dir / "run_meta.json") if (sample_dir / "run_meta.json").exists() else {}
        observation = load_json(sample_dir / "observation.json") if (sample_dir / "observation.json").exists() else {}
        coach = load_json(sample_dir / "coach_result.json") if (sample_dir / "coach_result.json").exists() else {}
        predicted = observation.get("action")
        expected = mapping.get(dataset["stroke_type"], {}).get("skill_action")
        if expected and predicted:
            confusion[str(expected)][str(predicted)] += 1
        issues = coach.get("issues", []) if coach.get("status") == "success" else []
        burden = sum(CONFIDENCE_WEIGHT.get(str(issue.get("confidence", "hypothesis")), 0.5) for issue in issues)
        row = {
            "sample_id": sample_id,
            "model": model_name,
            "stroke": dataset["stroke_type"],
            "quality_rating": dataset["quality_rating"],
            "quality_tier": dataset["quality_tier"],
            "schema_valid": bool(meta.get("schema_valid")),
            "pipeline_success": coach.get("status") == "success",
            "predicted_action": predicted,
            "expected_action": expected,
            "action_correct": bool(expected and predicted == expected),
            "num_issues": len(issues),
            "issue_burden": round(burden, 3),
            "primary_issue": issues[0].get("issue") if issues else None,
            "coach_confidence": coach.get("confidence"),
            "runtime_seconds": meta.get("runtime_seconds"),
            "missing_observations": len(observation.get("missing_observations", [])),
        }
        rows.append(row)
    total = len(rows)
    mapped = [row for row in rows if row["expected_action"]]
    tiers: dict[str, Any] = {}
    for tier in ("low", "medium", "high"):
        group = [row for row in rows if row["quality_tier"] == tier]
        tiers[tier] = {
            "samples": len(group),
            "average_issues": round(sum(row["num_issues"] for row in group) / len(group), 3) if group else None,
            "average_issue_burden": round(sum(row["issue_burden"] for row in group) / len(group), 3) if group else None,
            "average_missing_observations": round(sum(row["missing_observations"] for row in group) / len(group), 3) if group else None,
        }
    high = [row for row in rows if row["quality_tier"] == "high"]
    metrics = {
        "samples": total,
        "schema_success_rate": sum(row["schema_valid"] for row in rows) / total if total else 0,
        "pipeline_success_rate": sum(row["pipeline_success"] for row in rows) / total if total else 0,
        "stroke_recognition_accuracy": sum(row["action_correct"] for row in mapped) / len(mapped) if mapped else None,
        "quality_tiers": tiers,
        "high_quality_false_alarm_proxy": sum(row["num_issues"] >= 2 and row["coach_confidence"] == "high" for row in high) / len(high) if high else None,
        "low_vs_high_issue_separation": (tiers["low"]["average_issues"] - tiers["high"]["average_issues"]) if tiers["low"]["average_issues"] is not None and tiers["high"]["average_issues"] is not None else None,
        "low_vs_high_burden_separation": (tiers["low"]["average_issue_burden"] - tiers["high"]["average_issue_burden"]) if tiers["low"]["average_issue_burden"] is not None and tiers["high"]["average_issue_burden"] is not None else None,
        "average_runtime_seconds": round(sum(float(row["runtime_seconds"] or 0) for row in rows) / total, 3) if total else None,
        "confusion_matrix": {expected: dict(values) for expected, values in sorted(confusion.items())},
    }
    return metrics, rows


def build_report(metrics: dict[str, Any]) -> str:
    lines = [
        "# First-round public video benchmark report",
        "",
        "> Status: generated from the currently available runs. This report does not claim technical-error diagnosis accuracy.",
        "",
        "## Question 1 — Can a low-cost open Video VLM understand short badminton strokes?",
        "",
        "Measured through schema success and mapped stroke recognition; see the model table below.",
        "",
        "## Question 2 — Can its structured observations drive BadmintonCoachSkill reliably?",
        "",
        "Measured through end-to-end pipeline success. A run counts only when video decoding, VLM output, schema validation, and the existing Skill all complete.",
        "",
        "## Question 3 — Where does the pipeline fail?",
        "",
        "Failures are retained in per-sample run metadata and should be classified as action recognition, temporal understanding, fine-grained observation, hallucination, schema, or Skill coverage failures during case review.",
        "",
        "## Results",
        "",
        "| Model | Runs | Schema | Pipeline | Stroke accuracy | Low−High issues | Avg runtime |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model, value in metrics.get("models", {}).items():
        percentage = lambda number: "—" if number is None else f"{number * 100:.1f}%"
        separation = value.get("low_vs_high_issue_separation")
        runtime = value.get("average_runtime_seconds")
        lines.append(
            f"| {model} | {value['samples']} | {percentage(value['schema_success_rate'])} | {percentage(value['pipeline_success_rate'])} | {percentage(value['stroke_recognition_accuracy'])} | {'—' if separation is None else f'{separation:.2f}'} | {'—' if runtime is None else f'{runtime:.1f}s'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "BADS_CLL provides stroke type, quality rating, experience, and impact location. It does not provide fine-grained labels such as late arrival or low elbow. Detected issues are model-generated hypotheses, not ground-truth diagnoses.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/manifests/badminsense_60.json")
    args = parser.parse_args()
    manifest_rows = load_json(BENCHMARK_ROOT / args.manifest)
    manifest = {str(row["sample_id"]): row for row in manifest_rows}
    mapping = load_yaml(BENCHMARK_ROOT / "configs" / "action_mapping.yaml")
    all_rows: list[dict[str, Any]] = []
    model_metrics: dict[str, Any] = {}
    for model_name, model_config in config["inference"]["models"].items():
        metrics, rows = evaluate_model(model_name, BENCHMARK_ROOT / "results" / model_config["result_dir"], manifest, mapping)
        model_metrics[model_name] = metrics
        all_rows.extend(rows)
    summary = {"dataset": "BADS_CLL", "manifest_samples": len(manifest), "models": model_metrics, "metric_boundary": "Pipeline viability only; no fine-grained technical-error ground truth."}
    summary_dir = BENCHMARK_ROOT / "results" / "summary"
    write_json(summary_dir / "metrics.json", summary)
    summary_dir.mkdir(parents=True, exist_ok=True)
    with (summary_dir / "results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]) if all_rows else [])
        if all_rows:
            writer.writeheader()
            writer.writerows(all_rows)
    (summary_dir / "report.md").write_text(build_report(summary), encoding="utf-8")
    print(f"Wrote metrics for {len(all_rows)} model-sample rows")


if __name__ == "__main__":
    main()
