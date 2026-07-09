# Content Video Pipeline

This repository separates private video processing from public skill evidence.

## Flow

```text
source-index public URL
  -> video pilot manifest
  -> private metadata/audio/video/keyframe/model artifacts
  -> public timestamp evidence summaries
  -> human review
  -> skill framework, rubric, drill, or training-plan promotion
```

## Rules

- Raw videos, subtitles, cookies, tokens, OCR dumps, VLM dumps, ASR transcripts, and paid material stay out of git.
- Public evidence files may contain only original summaries, source ids, timestamps, topic tags, review status, and promotion decisions.
- `content_model_candidate` means a model parsed the content, but a human still needs to review it.
- `needs_content_model_review` means only metadata/title-level evidence exists; it must not be promoted into a deterministic skill rule.
- `source_backed` is reserved for reviewed timestamp evidence or explicitly reviewed short public clips.

## Pilot Result

The current ASR pilot covers 30 public Bilibili jobs from `data/corpus/video-pilot-manifest.yaml`.

- 25 jobs produced `content_model_candidate` evidence.
- 5 jobs remain `needs_content_model_review` because public Bilibili acquisition failed or timed out.
- 90 timestamp teaching windows were extracted into `data/corpus/video-asr-teaching-windows.yaml`.
- All 90 windows are `pending_human_review`.
- `faster-whisper tiny` was rejected because badminton terms were unstable.
- `mobiuslabsgmbh/faster-whisper-large-v3-turbo` is the preferred ASR model for candidate-window extraction after the pilot.

The successful pilot only parsed the first 180 seconds of each video. Full-video parsing should keep the same public/private boundary and should not promote model-only windows to firm rules until human review.

Compute-node runs should use a conda-built runtime, node-local model cache, and node-local audio/video intermediates to avoid shared-filesystem stalls. In the pilot, shared `/dataStor` Python environments could enter NFS wait states; the stable pattern was to unpack the conda environment and cache models under `/tmp` on the GPU node, then copy back only small public-safe JSON/YAML/log summaries.

## Commands

Build a pilot manifest:

```bash
python3 scripts/build_video_pilot_manifest.py --limit 30
```

Run public-safe metadata and evidence generation:

```bash
python3 scripts/run_video_content_pipeline.py --limit 3 --stages metadata,evidence
```

Run audio ASR pilot after installing `faster-whisper`:

```bash
python3 scripts/run_video_content_pipeline.py --limit 1 --stages metadata,audio,asr,evidence --asr-model small
```

Evaluate whether the pilot can be promoted:

```bash
python3 scripts/evaluate_video_pilot.py
```

Heavy model stages should run on a compute node, for example:

```bash
ssh <gpu-node> "cd <repo> && HF_HOME=<node-local-hf-cache> CUDA_VISIBLE_DEVICES=<gpu-id> <node-local-conda-env>/bin/python scripts/run_video_batch_on_node.py --limit 30 --batch-id <batch-id> --node-local-private-root <node-local-private-root> --asr-model mobiuslabsgmbh/faster-whisper-large-v3-turbo --asr-device cuda --asr-compute-type float16 --asr-audio-seconds 180"
```

Run a visual-understanding pilot after the compute node has a local Python environment with `torch`, `transformers`, `Pillow`, `opencv-python` or `imageio-ffmpeg`, `yt-dlp`, `PyYAML`, and enough GPU memory:

```bash
ssh <gpu-node> "cd <repo> && HF_HOME=<node-local-hf-cache> CUDA_VISIBLE_DEVICES=<gpu-id> <node-local-vision-env>/bin/python scripts/run_video_batch_on_node.py --job-id <job-id> --stages download,keyframes,vlm,evidence --batch-id <batch-id> --python <node-local-vision-env>/bin/python --hf-home <node-local-hf-cache> --hf-online --node-local-private-root <node-local-private-root> --keyframe-count 4 --vlm-model Qwen/Qwen2.5-VL-3B-Instruct"
```

The visual stages are dependency-optional:

- `keyframes` extracts private sampled frames with `imageio-ffmpeg` or OpenCV.
- `vlm` uses a Transformers-compatible vision-language model on private keyframes.
- `ocr` runs only when PaddleOCR is installed.
- `pose` runs only when Ultralytics pose is installed.

If a dependency is unavailable, the stage records `skipped`; it must not fabricate OCR, pose, or visual summaries. Public evidence still contains only status and original summaries, while private model outputs stay under `data/raw-private/` or node-local storage.

After a batch run, rebuild the public-safe index:

```bash
python3 scripts/rebuild_video_evidence_index.py
python3 scripts/evaluate_video_pilot.py
```
