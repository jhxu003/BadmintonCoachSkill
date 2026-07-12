from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from badminton_coach_skill.video_corpus import load_yaml  # noqa: E402
from run_video_content_pipeline import (  # noqa: E402
    build_asr_input,
    build_public_evidence,
    write_private_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run ASR for many already-downloaded video jobs while reusing one "
            "faster-whisper model instance."
        )
    )
    parser.add_argument("--manifest", default="data/corpus/video-corpus-manifest.yaml")
    parser.add_argument("--job-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--asr-model", default="mobiuslabsgmbh/faster-whisper-large-v3-turbo")
    parser.add_argument("--asr-device", default="cuda")
    parser.add_argument("--asr-compute-type", default="float16")
    parser.add_argument("--asr-audio-seconds", type=int, default=0)
    parser.add_argument("--skip-ok-asr", action="store_true")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--log-dir", default="data/raw-private/video-corpus/batch-runs")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_jobs(args: argparse.Namespace) -> list[dict[str, Any]]:
    manifest = load_yaml(ROOT / args.manifest)
    jobs = list(manifest.get("jobs", []))
    if args.job_id:
        requested = set(args.job_id)
        jobs = [job for job in jobs if job["job_id"] in requested]
    if args.offset:
        jobs = jobs[args.offset :]
    if args.limit:
        jobs = jobs[: args.limit]
    return jobs


def asr_already_ok(job: dict[str, Any]) -> bool:
    path = ROOT / job["private_paths"]["asr_json"]
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return data.get("status") == "ok"


def run_asr_with_model(
    job: dict[str, Any],
    model: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    private_path = ROOT / job["private_paths"]["asr_json"]
    audio_path = ROOT / job["private_paths"]["audio_file"]
    if not audio_path.exists():
        result = {
            "status": "skipped",
            "reason": "audio file missing; run audio stage first",
            "stage": "asr",
        }
        write_private_json(private_path, result)
        return result
    try:
        asr_input, audio_scope = build_asr_input(
            job,
            audio_path,
            args.asr_audio_seconds,
        )
        segments, info = model.transcribe(
            str(asr_input),
            language="zh",
            vad_filter=True,
            word_timestamps=False,
        )
        collected = []
        for segment in segments:
            text = " ".join(segment.text.strip().split())
            if not text:
                continue
            collected.append(
                {
                    "start": round(float(segment.start), 2),
                    "end": round(float(segment.end), 2),
                    "text": text,
                }
            )
        result = {
            "status": "ok",
            "stage": "asr",
            "model": args.asr_model,
            "device": args.asr_device,
            "compute_type": args.asr_compute_type,
            **audio_scope,
            "language": info.language,
            "language_probability": round(float(info.language_probability), 4),
            "segment_count": len(collected),
            "segments": collected,
        }
    except Exception as exc:
        result = {
            "status": "failed",
            "stage": "asr",
            "model": args.asr_model,
            "device": args.asr_device,
            "compute_type": args.asr_compute_type,
            "audio_scope_seconds": args.asr_audio_seconds or None,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    write_private_json(private_path, result)
    return result


def main() -> None:
    args = parse_args()
    batch_id = args.batch_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / args.log_dir / batch_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "summary.json"
    jobs = load_jobs(args)
    summary: dict[str, Any] = {
        "batch_id": batch_id,
        "started_at": utc_now(),
        "manifest": args.manifest,
        "asr_model": args.asr_model,
        "asr_device": args.asr_device,
        "asr_compute_type": args.asr_compute_type,
        "asr_audio_seconds": args.asr_audio_seconds,
        "jobs_requested": len(jobs),
        "results": [],
    }

    from faster_whisper import WhisperModel

    model = WhisperModel(
        args.asr_model,
        device=args.asr_device,
        compute_type=args.asr_compute_type,
    )
    for job in jobs:
        if args.skip_ok_asr and asr_already_ok(job):
            result = {
                "job_id": job["job_id"],
                "source_id": job["source_id"],
                "title": job["title"],
                "started_at": utc_now(),
                "finished_at": utc_now(),
                "returncode": 0,
                "timed_out": False,
                "asr_status": "ok",
                "asr_segment_count": None,
                "skipped": "private ASR already ok",
            }
        else:
            started_at = utc_now()
            asr_result = run_asr_with_model(job, model, args)
            run_status = {"job_id": job["job_id"], "stages": {"asr": asr_result}}
            evidence_path = build_public_evidence(job, run_status)
            write_private_json(ROOT / job["private_paths"]["run_log"], run_status)
            result = {
                "job_id": job["job_id"],
                "source_id": job["source_id"],
                "title": job["title"],
                "started_at": started_at,
                "finished_at": utc_now(),
                "returncode": 0 if asr_result.get("status") != "failed" else 1,
                "timed_out": False,
                "asr_status": asr_result.get("status", "unknown"),
                "asr_segment_count": asr_result.get("segment_count"),
                "evidence_path": str(evidence_path.relative_to(ROOT)),
            }
        summary["results"].append(result)
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"{job['job_id']}\treturncode={result['returncode']}\t"
            f"asr={result['asr_status']}\tsegments={result['asr_segment_count']}",
            flush=True,
        )
    summary["finished_at"] = utc_now()
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {display_path(summary_path)}")


if __name__ == "__main__":
    main()
