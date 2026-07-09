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

from badminton_coach_skill.video_corpus import load_yaml, write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a public-safe manifest from current private ASR status. "
            "Use it to retry only jobs whose ASR is not ok."
        )
    )
    parser.add_argument("--base-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--include-status",
        action="append",
        default=["missing", "skipped", "failed", "unreadable"],
    )
    return parser.parse_args()


def read_asr_status(job: dict[str, Any]) -> tuple[str, str]:
    path = ROOT / job["private_paths"]["asr_json"]
    if not path.exists():
        return "missing", "private ASR JSON missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return "unreadable", f"{type(exc).__name__}: {exc}"
    status = str(data.get("status", "missing"))
    reason = str(data.get("reason", ""))
    return status, reason


def main() -> None:
    args = parse_args()
    include_statuses = set(args.include_status)
    base = load_yaml(ROOT / args.base_manifest)
    jobs = []
    status_counts: Counter[str] = Counter()
    for job in base.get("jobs", []):
        status, reason = read_asr_status(job)
        status_counts[status] += 1
        if status not in include_statuses:
            continue
        updated = dict(job)
        updated["retry_reason"] = {
            "asr_status": status,
            "reason": reason,
        }
        updated["processing_status"] = "retry_pending"
        updated["review_status"] = "not_started"
        jobs.append(updated)
    manifest = {
        "manifest_id": f"asr_status_retry_manifest_{date.today().strftime('%Y%m%d')}",
        "created_at": date.today().isoformat(),
        "base_manifest": args.base_manifest,
        "include_statuses": sorted(include_statuses),
        "summary": {
            "retry_jobs": len(jobs),
            "asr_status_counts": dict(sorted(status_counts.items())),
        },
        "jobs": jobs,
    }
    write_yaml(ROOT / args.output, manifest)
    print(f"wrote {args.output}")
    print(f"retry_jobs {len(jobs)}")
    for status, count in sorted(status_counts.items()):
        print(f"{status} {count}")


if __name__ == "__main__":
    main()
