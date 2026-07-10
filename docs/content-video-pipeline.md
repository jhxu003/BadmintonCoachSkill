# Content Video Pipeline

This repository separates private video processing from public skill evidence.

## Flow

```text
public source index
  -> full-audio ASR and reviewed teaching windows
  -> teaching-window keyframes and structured Qwen3-VL visibility
  -> sparse Pose plus critical-window dense temporal Pose
  -> public-safe source/timestamp/framework/confidence evidence map
  -> skill framework, rubric, drill, and training-plan routing
```

## Corpus Scope

The completion target is the accessible non-YouTube public Bilibili index in this repository.

- Indexed Bilibili rows: 411.
- Discovery-only rows: 2.
- Independent video jobs: 409.
- Accessible videos: 408.
- Unavailable videos: 1.
- Reviewed ASR sources: 408.
- Reviewed ASR teaching windows: 2610.
- ASR-topic-confirmed windows: 2535.
- Title-supported windows: 75.
- Action or visible-demonstration sources: 402.
- ASR-only conceptual or equipment sources: 6.
- Planned sparse visual keyframes: 6064.
- Critical temporal sources: 204.
- Dense temporal sequences: 408.
- Dense temporal frames: 5304.

YouTube is excluded by project decision. Douyin and Instagram are retained as discovery-level access gaps and are not counted as parsed evidence.

## Evidence Rules

- Raw videos, audio, transcripts, keyframes, model dumps, Pose coordinates, cookies, tokens, and paid material stay out of git.
- Public evidence contains original summaries, source ids, timestamps, topic tags, framework links, evidence levels, visibility aggregates, and confidence boundaries.
- `asr_timestamp_reviewed_public_safe` supports topic routing and timestamp lookup, not visible mechanics.
- `asr_only_conceptual_public_safe` supports conceptual, equipment, and player-fit routing where no action-bearing visual scope exists.
- `visual_model_structured_candidate_public_safe` is Qwen3-VL v4 still-frame visibility evidence. It does not prove motion, contact, force, causality, or true joint rotation.
- `temporal_pose_proxy_public_safe` supports coarse monocular 2D change language. It does not prove racket face, shuttle contact, grip pressure, calibrated 3D kinematics, force, or true internal rotation.
- Model-only evidence must never be labeled as human coach review or Liu Hui's exact wording.

## Accepted Models

- ASR: `mobiuslabsgmbh/faster-whisper-large-v3-turbo`, full audio.
- Still-frame VLM: `Qwen3-VL-8B-Instruct`, artifact version 4, schema `visible_still_frame_v2`, batch size 1.
- Pose: Ultralytics `yolo11n-pose.pt`, private keypoints with public-safe visibility and geometry summaries.

Earlier `faster-whisper tiny`, Qwen2.5-VL-3B, and multi-frame VLM batching were evaluated and rejected for final corpus distillation.

## Reviewed Keyframe Selection

The 6064 sparse images are ASR-guided teaching-window samples, not automatically detected stroke-contact frames. Run the private review pass before treating them as useful teaching visuals:

```bash
python3 scripts/review_keyframe_quality.py \
  --artifact-root <shared-private-video-corpus> \
  --frame-root <node-local-keyframe-root> \
  --output-dir <shared-private-keyframe-review>
```

The review joins the planned timestamp, structured VLM visibility, Pose person coverage, and the extracted JPEG. It scores exposure, contrast, sharpness, subject scale, racket visibility, action-bearing body state, topic compatibility, and visibility limits. Frames with no visible person or unusable image content are rejected; neutral-standing, cropped, small-subject, and racket-missing frames are penalized. Perceptual hashes suppress near duplicates within the same teaching window, and no more than three distinct frames are retained per window.

Private outputs include a frame-level inventory, selection reasons, summary counts, an accepted/rejected comparison, a representative selected-frame sheet, and topic-specific contact sheets. These files remain under `data/raw-private/` and must not be committed.

## Reproducible Environment

Create the video-processing environment from the pinned project file:

```bash
conda env create -f environment-video.yml
conda activate badminton-coach-video
```

Heavy ASR, VLM, Pose, and frame extraction must run on a compute node. `/dataStor` is shared across nodes, but each node has an independent `/tmp`; keep models, media, and large intermediates in node-local storage and copy back only the small private artifacts required for consolidation.

## Build And Reduce

Build the current ASR and visual manifests:

```bash
python3 scripts/build_asr_teaching_windows.py
python3 scripts/build_asr_timestamp_review.py
python3 scripts/build_visual_review_manifest.py
python3 scripts/build_visual_pipeline_manifest.py
python3 scripts/build_temporal_review_manifest.py
```

Run a selected private visual job on a GPU node:

```bash
CUDA_VISIBLE_DEVICES=0 python3 scripts/run_video_content_pipeline.py \
  --manifest data/corpus/video-visual-pipeline-manifest.yaml \
  --job-id <job-id> \
  --stages vlm,pose \
  --keyframe-source visual-review \
  --vlm-model <local-qwen3-vl-8b-path> \
  --vlm-max-new-tokens 256 \
  --vlm-batch-size 1 \
  --private-root-override <node-local-private-root> \
  --skip-public-evidence
```

After private artifacts are consolidated under ignored `data/raw-private/`, rebuild the public-safe layer:

```bash
python3 scripts/build_visual_completion_status.py
python3 scripts/build_visual_evidence_summary.py \
  --manifest data/corpus/video-visual-pipeline-manifest.yaml
python3 scripts/build_temporal_pose_summary.py
python3 scripts/build_multimodal_skill_evidence.py
python3 scripts/audit_multimodal_completion.py
```

`data/corpus/multimodal-completion-status.yaml` is the machine-readable completion result. A wrapper exit code alone is not completion; every required artifact and explainability link must pass its audit gate.
