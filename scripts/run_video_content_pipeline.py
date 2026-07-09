from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from badminton_coach_skill.video_corpus import load_yaml, write_evidence_index, write_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run public-video content parsing jobs and emit public-safe timestamp evidence."
    )
    parser.add_argument(
        "--manifest",
        default="data/corpus/video-pilot-manifest.yaml",
        help="Pilot manifest YAML.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N jobs. 0 means all jobs.",
    )
    parser.add_argument(
        "--job-id",
        action="append",
        default=[],
        help="Process only the given job id. Can be passed more than once.",
    )
    parser.add_argument(
        "--stages",
        default="metadata,evidence",
        help=(
            "Comma-separated stages: metadata,audio,download,asr,ocr,vlm,pose,evidence. "
            "Unavailable model stages are recorded as skipped rather than faked."
        ),
    )
    parser.add_argument(
        "--evidence-index",
        default="data/corpus/video-evidence-index.tsv",
    )
    parser.add_argument(
        "--asr-model",
        default="large-v3-turbo",
        help="faster-whisper model size or local model path.",
    )
    parser.add_argument(
        "--asr-device",
        default="auto",
        help="faster-whisper device: auto, cpu, or cuda.",
    )
    parser.add_argument(
        "--asr-compute-type",
        default="auto",
        help="faster-whisper compute type, for example auto, int8, float16.",
    )
    parser.add_argument(
        "--asr-audio-seconds",
        type=int,
        default=0,
        help="Transcribe only the first N seconds for model-quality pilots. 0 means full audio.",
    )
    parser.add_argument("--metadata-timeout", type=int, default=120)
    parser.add_argument("--audio-timeout", type=int, default=240)
    parser.add_argument("--download-timeout", type=int, default=600)
    parser.add_argument("--yt-dlp-socket-timeout", type=int, default=30)
    parser.add_argument("--yt-dlp-retries", type=int, default=2)
    parser.add_argument(
        "--private-root-override",
        default="",
        help=(
            "Override private artifact root for this run. Use an absolute node-local "
            "path on compute nodes to avoid writing large audio/video artifacts to NFS."
        ),
    )
    return parser.parse_args()


def run_command(
    command: list[str],
    output_path: Path | None = None,
    timeout_seconds: int = 0,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds or None,
        )
        record = {
            "command": command,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": 124,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
        }
    if output_path and result.returncode == 0:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.stdout, encoding="utf-8")
    return record


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def yt_dlp_command() -> list[str] | None:
    if import_available("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    if command_exists("yt-dlp"):
        return ["yt-dlp"]
    return None


def yt_dlp_network_options(args: argparse.Namespace) -> list[str]:
    return [
        "--socket-timeout",
        str(args.yt_dlp_socket_timeout),
        "--retries",
        str(args.yt_dlp_retries),
        "--fragment-retries",
        str(args.yt_dlp_retries),
        "--extractor-retries",
        str(args.yt_dlp_retries),
        "--retry-sleep",
        "1",
    ]


def write_private_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_private_root_override(job: dict[str, Any], private_root: str) -> dict[str, Any]:
    if not private_root:
        return job
    updated = copy.deepcopy(job)
    root = Path(private_root).expanduser()
    if not root.is_absolute():
        root = ROOT / root
    job_dir = root / job["job_id"]
    updated["private_paths"] = {
        "job_dir": str(job_dir),
        "metadata_json": str(job_dir / "metadata.json"),
        "video_file": str(job_dir / "source_video"),
        "audio_file": str(job_dir / "audio.m4a"),
        "keyframes_dir": str(job_dir / "keyframes"),
        "asr_json": str(job_dir / "asr.json"),
        "ocr_json": str(job_dir / "ocr.json"),
        "vlm_json": str(job_dir / "vlm.json"),
        "pose_json": str(job_dir / "pose.json"),
        "run_log": str(job_dir / "run.log"),
    }
    return updated


def run_metadata(job: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    path = ROOT / job["private_paths"]["metadata_json"]
    if path.exists() and path.stat().st_size > 0:
        return {"status": "ok", "reason": "metadata already exists"}
    base_command = yt_dlp_command()
    if not base_command:
        return {"status": "skipped", "reason": "yt-dlp not found"}
    record = run_command(
        [
            *base_command,
            *yt_dlp_network_options(args),
            "--dump-json",
            "--no-warnings",
            job["url"],
        ],
        path,
        timeout_seconds=args.metadata_timeout,
    )
    return {"status": "ok" if record["returncode"] == 0 else "failed", "record": record}


def run_download(job: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    path = ROOT / job["private_paths"]["video_file"]
    output_template = str(path) + ".%(ext)s"
    base_command = yt_dlp_command()
    if not base_command:
        return {"status": "skipped", "reason": "yt-dlp not found"}
    command = [
        *base_command,
        *yt_dlp_network_options(args),
        "--no-playlist",
        "-f",
        "best[ext=mp4]/best",
        "-o",
        output_template,
        job["url"],
    ]
    record = run_command(command, timeout_seconds=args.download_timeout)
    return {"status": "ok" if record["returncode"] == 0 else "failed", "record": record}


def run_audio(job: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    path = ROOT / job["private_paths"]["audio_file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return {
            "status": "ok",
            "reason": "audio already exists",
            "private_audio_path": str(path),
        }
    base_command = yt_dlp_command()
    if not base_command:
        return {"status": "skipped", "reason": "yt-dlp not found"}
    command = [
        *base_command,
        *yt_dlp_network_options(args),
        "--no-playlist",
        "-f",
        "ba[ext=m4a]/bestaudio[ext=m4a]/bestaudio",
        "-o",
        str(path),
        job["url"],
    ]
    record = run_command(command, timeout_seconds=args.audio_timeout)
    return {
        "status": "ok" if record["returncode"] == 0 and path.exists() else "failed",
        "record": record,
        "private_audio_path": str(path),
    }


def import_available(module_name: str) -> bool:
    try:
        __import__(module_name)
    except Exception:
        return False
    return True


def run_model_stage(job: dict[str, Any], stage: str, module_name: str) -> dict[str, Any]:
    private_path = ROOT / job["private_paths"][f"{stage}_json"]
    if not import_available(module_name):
        result = {
            "status": "skipped",
            "reason": f"{module_name} is not installed in this Python environment",
            "stage": stage,
        }
        write_private_json(private_path, result)
        return result
    result = {
        "status": "needs_worker",
        "reason": (
            f"{stage} dependency is available, but the heavyweight worker should be "
            "launched on a GPU node with the project-specific model checkpoint."
        ),
        "stage": stage,
    }
    write_private_json(private_path, result)
    return result


def build_asr_input(job: dict[str, Any], audio_path: Path, seconds: int) -> tuple[Path, dict[str, Any]]:
    if seconds <= 0:
        return audio_path, {"audio_scope_seconds": None, "audio_scope": "full"}
    clipped_path = audio_path.with_name(f"asr-preview-{seconds}s.wav")
    if clipped_path.exists():
        return clipped_path, {"audio_scope_seconds": seconds, "audio_scope": "preview"}
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except Exception as exc:
        return audio_path, {
            "audio_scope_seconds": None,
            "audio_scope": "full",
            "clip_warning": f"imageio_ffmpeg unavailable: {type(exc).__name__}: {exc}",
        }
    command = [
        get_ffmpeg_exe(),
        "-y",
        "-i",
        str(audio_path),
        "-t",
        str(seconds),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(clipped_path),
    ]
    record = run_command(command)
    if record["returncode"] != 0 or not clipped_path.exists():
        return audio_path, {
            "audio_scope_seconds": None,
            "audio_scope": "full",
            "clip_warning": "ffmpeg clipping failed; full audio was used",
        }
    return clipped_path, {"audio_scope_seconds": seconds, "audio_scope": "preview"}


def run_asr(
    job: dict[str, Any],
    model_size: str,
    device: str,
    compute_type: str,
    audio_seconds: int,
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
        from faster_whisper import WhisperModel
    except Exception as exc:
        result = {
            "status": "skipped",
            "reason": f"faster_whisper import failed: {type(exc).__name__}: {exc}",
            "stage": "asr",
        }
        write_private_json(private_path, result)
        return result

    try:
        asr_input, audio_scope = build_asr_input(job, audio_path, audio_seconds)
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
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
            "model": model_size,
            "device": device,
            "compute_type": compute_type,
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
            "model": model_size,
            "device": device,
            "compute_type": compute_type,
            "audio_scope_seconds": audio_seconds or None,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    write_private_json(private_path, result)
    return result


def summarize_private_stage(job: dict[str, Any], stage: str) -> dict[str, Any]:
    path = ROOT / job["private_paths"].get(f"{stage}_json", "")
    if not path.exists():
        return {"status": "missing"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "unreadable", "reason": str(exc)}


def summarize_asr_for_public(asr_data: dict[str, Any]) -> str:
    if asr_data.get("status") != "ok":
        return "ASR did not produce usable timestamped content."
    segments = asr_data.get("segments", [])
    if not segments:
        return "ASR ran but produced no usable speech segments."
    early_segments = segments[:6]
    windows = [
        f"{item['start']:.1f}-{item['end']:.1f}s"
        for item in early_segments
        if "start" in item and "end" in item
    ]
    return (
        f"Private ASR produced {len(segments)} timestamped Chinese speech segments. "
        f"Initial reviewed windows for human summarization: {', '.join(windows)}."
    )


def summarize_missing_or_private(stage_name: str, data: dict[str, Any]) -> str:
    if data.get("status") == "ok":
        return f"See private {stage_name} artifact; public summary requires human review."
    return f"No {stage_name.upper()} content was promoted into the public repository."


def sanitize_stage_status(stage: str, data: dict[str, Any]) -> dict[str, Any]:
    status = {"status": data.get("status", "missing")}
    if data.get("reason"):
        status["reason"] = data["reason"]
    if stage == "asr":
        for field in [
            "stage",
            "model",
            "device",
            "compute_type",
            "language",
            "language_probability",
            "segment_count",
        ]:
            if field in data:
                status[field] = data[field]
        if "audio_scope" in data:
            status["audio_scope"] = data["audio_scope"]
        if "audio_scope_seconds" in data:
            status["audio_scope_seconds"] = data["audio_scope_seconds"]
    return status


def sanitize_run_status(run_status: dict[str, Any]) -> dict[str, Any]:
    sanitized = {"job_id": run_status.get("job_id"), "stages": {}}
    for stage, value in run_status.get("stages", {}).items():
        if not isinstance(value, dict):
            sanitized["stages"][stage] = {"status": "unknown"}
            continue
        stage_record = {"status": value.get("status", "unknown")}
        if value.get("reason"):
            stage_record["reason"] = value["reason"]
        record = value.get("record")
        if isinstance(record, dict):
            stage_record["returncode"] = record.get("returncode")
        sanitized["stages"][stage] = stage_record
    return sanitized


def build_public_evidence(job: dict[str, Any], run_status: dict[str, Any]) -> Path:
    evidence_path = ROOT / job["public_outputs"]["timestamp_evidence"]
    stage_status = {
        stage: summarize_private_stage(job, stage)
        for stage in ["asr", "ocr", "vlm", "pose"]
    }
    has_model_content = any(
        value.get("status") == "ok" for value in stage_status.values()
    )
    evidence_level = (
        "content_model_candidate" if has_model_content else "needs_content_model_review"
    )
    review_status = "pending_human_review" if has_model_content else "model_not_run"
    segment = {
        "evidence_id": f"{job['job_id']}-seg-001",
        "start_seconds": 0,
        "end_seconds": None,
        "topic_tags": job["priority_topics"],
        "evidence_level": evidence_level,
        "review_status": review_status,
        "promotion_target": "none_until_reviewed",
        "asr_summary": summarize_asr_for_public(stage_status["asr"]),
        "ocr_summary": summarize_missing_or_private("OCR", stage_status["ocr"]),
        "visual_summary": summarize_missing_or_private("VLM", stage_status["vlm"]),
        "teaching_point_candidate": {
            "problem": "pending content-level model review",
            "diagnosis_rule": "not promoted",
            "correction": "not promoted",
            "drill": "not promoted",
        },
    }
    evidence = {
        "source_id": job["source_id"],
        "job_id": job["job_id"],
        "title": job["title"],
        "url": job["url"],
        "platform": job["platform"],
        "authorization_status": job["authorization_status"],
        "public_safety": {
            "raw_video_committed": False,
            "raw_transcript_committed": False,
            "paid_material_committed": False,
            "long_subtitle_excerpt_committed": False,
            "raw_metadata_committed": False,
            "temporary_media_urls_committed": False,
        },
        "run_status": sanitize_run_status(run_status),
        "stage_status": {
            stage: sanitize_stage_status(stage, data)
            for stage, data in stage_status.items()
        },
        "segments": [segment],
    }
    write_yaml(evidence_path, evidence)
    return evidence_path


def process_job(job: dict[str, Any], stages: set[str], args: argparse.Namespace) -> Path:
    job_dir = ROOT / job["private_paths"]["job_dir"]
    job_dir.mkdir(parents=True, exist_ok=True)
    run_status: dict[str, Any] = {"job_id": job["job_id"], "stages": {}}
    if "metadata" in stages:
        run_status["stages"]["metadata"] = run_metadata(job, args)
    if "audio" in stages:
        run_status["stages"]["audio"] = run_audio(job, args)
    if "download" in stages:
        run_status["stages"]["download"] = run_download(job, args)
    if "asr" in stages:
        run_status["stages"]["asr"] = run_asr(
            job,
            model_size=args.asr_model,
            device=args.asr_device,
            compute_type=args.asr_compute_type,
            audio_seconds=args.asr_audio_seconds,
        )
    if "ocr" in stages:
        run_status["stages"]["ocr"] = run_model_stage(job, "ocr", "paddleocr")
    if "vlm" in stages:
        run_status["stages"]["vlm"] = run_model_stage(job, "vlm", "transformers")
    if "pose" in stages:
        run_status["stages"]["pose"] = run_model_stage(job, "pose", "cv2")
    if "evidence" not in stages:
        stages.add("evidence")
    evidence_path = build_public_evidence(job, run_status)
    write_private_json(ROOT / job["private_paths"]["run_log"], run_status)
    return evidence_path


def main() -> None:
    args = parse_args()
    manifest = load_yaml(ROOT / args.manifest)
    jobs = manifest.get("jobs", [])
    if args.job_id:
        requested = set(args.job_id)
        jobs = [job for job in jobs if job["job_id"] in requested]
    if args.limit:
        jobs = jobs[: args.limit]
    jobs = [apply_private_root_override(job, args.private_root_override) for job in jobs]
    stages = {item.strip() for item in args.stages.split(",") if item.strip()}
    evidence_files = [process_job(job, stages, args) for job in jobs]
    write_evidence_index(ROOT / args.evidence_index, evidence_files)
    print(f"processed {len(evidence_files)} jobs")
    print(f"wrote {args.evidence_index}")


if __name__ == "__main__":
    main()
