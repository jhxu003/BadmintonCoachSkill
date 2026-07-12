from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project private semantic candidates into public-safe review data.")
    parser.add_argument("--input-root", default="data/raw-private/li-yuxuan/semantic-claims-progress")
    parser.add_argument("--output", default="data/coaches/li-yuxuan/corpus/video-semantic-claim-review.yaml")
    return parser.parse_args()


def public_projection(item: dict[str, Any]) -> dict[str, Any]:
    windows = [
        {key: window.get(key) for key in ["window_id", "start_seconds", "end_seconds"]}
        for window in item.get("windows", [])
        if isinstance(window, dict)
    ]
    claims = [
        {
            "claim_id": claim.get("claim_id"),
            "claim_type": claim.get("claim_type"),
            "normalized_statement": claim.get("normalized_statement"),
            "observation_preconditions": claim.get("observation_preconditions", []),
            "support_window_ids": claim.get("support_window_ids", []),
            "visual_confirmation_required": True,
            "evidence_level": claim.get("evidence_level", "semantic_model_candidate_private"),
            "promotion_status": "requires_cross_source_and_visual_review",
        }
        for claim in item.get("claims", [])
        if isinstance(claim, dict)
    ]
    return {"job_id": item.get("job_id"), "source_id": item.get("source_id"), "title": item.get("title"), "status": item.get("status"), "topic_tags": item.get("topic_tags", []), "windows": windows, "claims": claims, "boundary": "Public-safe semantic candidate index; not a quote, human coach review, or visual biomechanical proof."}


def main() -> None:
    args = parse_args()
    root = ROOT / args.input_root
    inputs = []
    statuses: Counter[str] = Counter()
    topics: Counter[str] = Counter()
    claims = 0
    for path in sorted(root.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(item, dict):
            continue
        statuses[str(item.get("status", "unknown"))] += 1
        if item.get("status") != "ok":
            continue
        projected = public_projection(item)
        inputs.append(projected)
        topics.update(str(topic) for topic in projected["topic_tags"])
        claims += len(projected["claims"])
    write_yaml(ROOT / args.output, {"semantic_claim_review": {"created_at": date.today().isoformat(), "scope": "Public-safe projection of private semantic model candidates. Raw ASR, prompts, and model responses remain private.", "summary": {"files_scanned": sum(statuses.values()), "status_counts": dict(statuses), "sources_with_ok_semantic_candidates": len(inputs), "claims": claims, "topic_claim_source_counts": dict(topics)}, "promotion_boundary": "Every candidate requires cross-source consistency review and, for action claims, compatible visual evidence before use as a deterministic Skill rule."}, "sources": inputs})
    print(f"wrote {args.output}")
    print(f"sources {len(inputs)} claims {claims}")


if __name__ == "__main__":
    main()
