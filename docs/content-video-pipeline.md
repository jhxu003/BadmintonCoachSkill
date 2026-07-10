# Content Video Pipeline

This repository separates private video processing from public skill evidence.

## Flow

```text
source-index public URL
  -> video manifest
  -> private metadata/audio/video/keyframe/model artifacts
  -> public ASR timestamp review and visual visibility summaries
  -> human review
  -> skill framework, rubric, drill, or training-plan promotion
```

## Rules

- Raw videos, subtitles, cookies, tokens, OCR dumps, VLM dumps, ASR transcripts, and paid material stay out of git.
- Public evidence files may contain only original summaries, source ids, timestamps, topic tags, review status, and promotion decisions.
- `content_model_candidate` means a model parsed the content, but a human still needs to review it.
- `asr_timestamp_reviewed_public_safe` means the private ASR interval was checked and reduced to an original topic/timestamp summary; it supports routing but not visual mechanics.
- `visual_model_candidate_reviewed_public_safe` and `pose_model_candidate_reviewed_public_safe` locate timestamps with usable visibility; they do not independently prove biomechanics.
- `needs_content_model_review` means only metadata/title-level evidence exists; it must not be promoted into a deterministic skill rule.
- `source_backed` is reserved for reviewed timestamp evidence or explicitly reviewed short public clips.

## Current Result

The first content-model pilot covered 30 public Bilibili jobs from `data/corpus/video-pilot-manifest.yaml`. The current main corpus run then expanded to the indexed public Bilibili corpus in `data/corpus/video-corpus-manifest.yaml`.

- Pilot jobs: 30.
- Expanded Bilibili corpus jobs: 379.
- Full-audio ASR completed: 378 of 379 expanded corpus jobs.
- Unavailable public page: `LH_BILI_CORE_COMPETITION`.
- Combined pilot + corpus jobs scanned for teaching windows: 409.
- Sources with candidate windows: 401.
- Public-safe timestamp candidate windows: 2567 in `data/corpus/video-asr-teaching-windows-full.yaml`.
- Public-safe agent-reviewed ASR windows: 2567 in `data/corpus/video-asr-timestamp-review.yaml`.
- Action-bearing visual review jobs: 396 with 5977 planned keyframes in `data/corpus/video-visual-review-manifest.yaml`.
- Existing private VLM summaries: 30 sources and 336 keyframes in `data/corpus/video-visual-evidence-summary.yaml`.
- Representative private pose summaries: 6 sources and 107 keyframes, all with detected people, in `data/corpus/video-pose-evidence-summary.yaml`.
- `faster-whisper tiny` was rejected because badminton terms were unstable.
- `mobiuslabsgmbh/faster-whisper-large-v3-turbo` is the accepted ASR model for candidate-window extraction.
- `Qwen2.5-VL-3B-Instruct` with teaching-window-guided keyframe sampling remains the accepted visual candidate-review model from the pilot.

The expanded Bilibili ASR pass parsed full audio and every selected teaching window now has a public-safe agent review. The visual layer uses sampled teaching-window keyframes rather than dense full-video understanding. Model-only visual or pose output must not become a firm biomechanical rule until a human reviews the referenced frames.

`/dataStor` is shared across compute nodes, while each node has an independent `/tmp`. Keep large video, audio, keyframe, and model intermediates under the selected GPU node's `/tmp`, and copy back only small JSON/YAML/log summaries. A shared Conda environment may be used when that node reads NFS normally; if imports enter an NFS wait state, move the runtime or switch to a healthy node rather than moving heavy media back to the shared filesystem.

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

Build the expanded public Bilibili corpus manifest:

```bash
python3 scripts/build_video_corpus_manifest.py
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
```

Build the reviewed ASR and visual coverage artifacts:

```bash
python3 scripts/build_asr_timestamp_review.py --manifest data/corpus/video-pilot-manifest.yaml --manifest data/corpus/video-corpus-manifest.yaml
python3 scripts/build_visual_review_manifest.py --manifest data/corpus/video-pilot-manifest.yaml --manifest data/corpus/video-corpus-manifest.yaml
python3 scripts/build_visual_evidence_summary.py --manifest data/corpus/video-pilot-manifest.yaml --manifest data/corpus/video-corpus-manifest.yaml
python3 scripts/build_pose_evidence_summary.py --manifest data/corpus/video-pilot-manifest.yaml --manifest data/corpus/video-corpus-manifest.yaml
```
