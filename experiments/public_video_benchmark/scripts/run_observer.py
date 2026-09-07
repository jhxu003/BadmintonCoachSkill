#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
from typing import Any

import jsonschema

from common import (
    BENCHMARK_ROOT,
    CONFIG_PATH,
    PROJECT_ROOT,
    SCHEMA_PATH,
    ensure_import_path,
    git_commit,
    load_json,
    load_yaml,
    resolve_benchmark_path,
    sha256_file,
    sha256_text,
    write_json,
)

ensure_import_path()
from badminton_coach_skill.coach_registry import load_coach_knowledge  # noqa: E402
from badminton_coach_skill.video_evidence.agent import (  # noqa: E402
    observation_value_whitelist,
    validate_agent_observation,
)

from observers.base import extract_json, sample_gif  # noqa: E402
from observers.qwen25_vl import Qwen25VLObserver  # noqa: E402
from observers.qwen3_vl import Qwen3VLObserver  # noqa: E402


OBSERVERS = {"qwen3-vl-2b": Qwen3VLObserver, "qwen25-vl-3b": Qwen25VLObserver}


def smoke_subset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result = []
    for row in rows:
        cell = (str(row["stroke_type"]), str(row["quality_tier"]))
        if cell not in seen:
            result.append(row)
            seen.add(cell)
    return result


def environment_payload() -> dict[str, Any]:
    import torch
    import transformers

    return {
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def render_prompt(template: str, schema: dict[str, Any], vocab: dict[str, Any], timestamps: tuple[float, ...], repair: bool) -> str:
    return template.format(
        schema_json=json.dumps(schema, ensure_ascii=False),
        action_values=json.dumps(schema["properties"]["action"]["enum"], ensure_ascii=False),
        allowed_values=json.dumps(vocab, ensure_ascii=False),
        frame_timestamps=json.dumps([round(value, 1) for value in timestamps]),
        repair_instruction=(
            "Your previous response did not satisfy the required JSON schema. Return corrected JSON only."
            if repair
            else ""
        ),
    )


def main() -> None:
    config = load_yaml(CONFIG_PATH)
    parser = argparse.ArgumentParser(description="Run a zero-shot local Video VLM observer.")
    parser.add_argument("--model", choices=sorted(OBSERVERS), required=True)
    parser.add_argument("--manifest", default="data/manifests/badminsense_60.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--smoke", action="store_true", help="Choose one sample from each stroke-quality cell.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--model-path")
    args = parser.parse_args()

    model_config = config["inference"]["models"][args.model]
    model_path = args.model_path or str(PROJECT_ROOT / model_config["local_dir"])
    if not Path(model_path).exists():
        model_path = str(model_config["model_id"])
    rows = load_json(resolve_benchmark_path(args.manifest))
    if args.smoke:
        rows = smoke_subset(rows)
    if args.limit:
        rows = rows[: args.limit]

    schema = load_json(SCHEMA_PATH)
    template = (BENCHMARK_ROOT / "prompts" / "video_observer.txt").read_text(encoding="utf-8")
    mappings = load_yaml(BENCHMARK_ROOT / "configs" / "action_mapping.yaml")
    knowledge = load_coach_knowledge(str(config["skill"]["coach_id"]), PROJECT_ROOT)
    knowledge_sets = [knowledge]
    vocab = {
        action: observation_value_whitelist(knowledge_sets, action)
        for action in schema["properties"]["action"]["enum"]
    }
    observer = OBSERVERS[args.model](model_path, max_new_tokens=int(config["inference"]["max_new_tokens"]))
    result_root = BENCHMARK_ROOT / "results" / str(model_config["result_dir"])
    raw_dataset_root = BENCHMARK_ROOT / "data" / "raw" / "BADS_CLL"
    prompt_base_hash = sha256_text(template + json.dumps(vocab, sort_keys=True))
    schema_hash = sha256_file(SCHEMA_PATH)
    completed = 0
    try:
        for row in rows:
            sample_id = str(row["sample_id"])
            media = raw_dataset_root / str(row["media_path"])
            output_dir = result_root / sample_id
            meta_path = output_dir / "run_meta.json"
            media_hash = sha256_file(media)
            cache_key = sha256_text("|".join((media_hash, prompt_base_hash, schema_hash, str(model_config["model_id"]), str(config["inference"]))))
            if meta_path.exists() and not args.force:
                old = load_json(meta_path)
                if old.get("cache_key") == cache_key and (output_dir / "observation.json").exists():
                    print(f"cached {sample_id}")
                    completed += 1
                    continue
            clip = sample_gif(media, float(config["inference"]["sampling_fps"]), int(config["inference"]["max_frames"]))
            output_dir.mkdir(parents=True, exist_ok=True)
            attempts: list[str] = []
            parsed: dict[str, Any] | None = None
            error: str | None = None
            total_runtime = 0.0
            device = "unknown"
            for retry in range(int(config["inference"]["retry_count"]) + 1):
                prompt = render_prompt(template, schema, vocab, clip.timestamps_ms, retry > 0)
                try:
                    raw, runtime, device = observer.generate(clip, prompt)
                    total_runtime += runtime
                    attempts.append(raw)
                    candidate = extract_json(raw)
                    jsonschema.validate(candidate, schema)
                    parsed = candidate
                    error = None
                    break
                except Exception as exc:  # inference and validation are persisted for audit
                    error = f"{type(exc).__name__}: {exc}"
            (output_dir / "raw_output.txt").write_text("\n\n--- RETRY ---\n\n".join(attempts), encoding="utf-8")
            schema_valid = parsed is not None
            accepted = False
            observation = parsed
            if parsed is not None:
                predicted = str(parsed.get("action", "unknown"))
                validation = validate_agent_observation(
                    action=predicted,
                    raw_observation=parsed,
                    base_observation={"camera_view": parsed.get("camera_view", "unknown"), "fps_quality": parsed.get("fps_quality", "unknown"), "keyframes": parsed.get("keyframes", []), "missing_observations": parsed.get("missing_observations", [])},
                    knowledge_sets=knowledge_sets,
                    minimum_confidence="high",
                )
                observation = validation.observation
                jsonschema.validate(observation, schema)
                accepted = validation.accepted
                write_json(output_dir / "observation.json", observation)
            meta = {
                "model": model_config["model_id"],
                "model_path": model_path,
                "sample_id": sample_id,
                "sampling_fps": config["inference"]["sampling_fps"],
                "num_frames": len(clip.frames),
                "source_frame_count": clip.source_frame_count,
                "duration_ms": clip.duration_ms,
                "schema_valid": schema_valid,
                "rubric_observation_accepted": accepted,
                "retry_count": max(0, len(attempts) - 1),
                "runtime_seconds": round(total_runtime, 3),
                "device": device,
                "error": error,
                "cache_key": cache_key,
                "media_sha256": media_hash,
                "prompt_sha256": prompt_base_hash,
                "schema_sha256": schema_hash,
                "dataset_action": row["stroke_type"],
                "mapped_skill_action": mappings.get(row["stroke_type"], {}).get("skill_action"),
                "environment": environment_payload(),
            }
            write_json(meta_path, meta)
            print(f"{sample_id}: schema_valid={schema_valid}, runtime={total_runtime:.1f}s")
            completed += 1
    finally:
        observer.close()
    summary_dir = BENCHMARK_ROOT / "results" / "summary"
    write_json(summary_dir / "environment.json", environment_payload())
    print(f"Completed {completed}/{len(rows)} observations")


if __name__ == "__main__":
    main()
