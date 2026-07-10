# Full Multimodal Liu Hui Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Process every accessible non-YouTube action-bearing Liu Hui source with exact teaching-window VLM and Pose evidence, add critical-source temporal proxies, and distill the results into the Skill.

**Architecture:** Build an executable visual manifest from the reviewed corpus, run resumable node-local GPU shards, reduce private model artifacts into public-safe evidence, and repeatedly audit gaps until every source has a terminal status. The existing ASR corpus remains the routing layer; visual and temporal evidence strengthen only observable claims.

**Tech Stack:** Python 3.10, PyYAML, yt-dlp, imageio-ffmpeg/OpenCV, Qwen2.5-VL-3B, PyTorch, Ultralytics YOLO pose, Git/GitHub.

## Global Constraints

- YouTube is excluded.
- No test/eval directories or files are published; verification uses executable scripts and examples.
- Raw media, transcripts, VLM text, keyframes, Pose coordinates, cookies, tokens, and model weights stay private.
- Heavy work runs on compute nodes with node-local storage.
- A stage is complete only when its artifact status is `ok`, not merely when the wrapper exits zero.

---

### Task 1: Executable Visual Manifest

**Files:**
- Create: `scripts/build_visual_pipeline_manifest.py`
- Create: `data/corpus/video-visual-pipeline-manifest.yaml`
- Modify: `scripts/run_video_content_pipeline.py`
- Modify: `scripts/run_video_batch_on_node.py`

- [ ] Join all 396 visual-review jobs to original pipeline job definitions.
- [ ] Preserve exact `planned_frames` and visual review targets per job.
- [ ] Add `visual-review` as a keyframe source and extract every planned timestamp.
- [ ] Emit requested, extracted, and failed frame counts.
- [ ] Verify manifest counts are 396 jobs and 5977 planned frames.

### Task 2: Structured Full-Corpus VLM And Pose Artifacts

**Files:**
- Modify: `scripts/run_video_content_pipeline.py`
- Modify: `scripts/run_video_batch_on_node.py`
- Create: `scripts/build_visual_completion_status.py`

- [ ] Make VLM prompts explicitly preserve timestamp-to-image ordering and visible-only evidence.
- [ ] Retain private Pose keypoints and bounding data needed for later geometry summaries.
- [ ] Add skip/resume controls for existing successful VLM and Pose artifacts.
- [ ] Build terminal status and retry manifests from artifact contents.
- [ ] Verify failed stages cannot be counted as successful jobs.

### Task 3: GPU Sharded Full Run

**Files:**
- Private only: `data/raw-private/video-corpus/batch-runs/`
- Private only: node-local shard roots under `/tmp`

- [ ] Select healthy GPU nodes and copy the local VLM runtime/model where needed.
- [ ] Split pending jobs into deterministic shards.
- [ ] Run `download,keyframes,vlm,pose` for every pending action source.
- [ ] Copy private JSON/log artifacts back after each shard.
- [ ] Generate retries until every source is `ok` or concretely unavailable.

### Task 4: Critical Temporal Evidence

**Files:**
- Create: `scripts/build_temporal_review_manifest.py`
- Create: `scripts/build_temporal_pose_summary.py`
- Create: `data/corpus/video-temporal-review-manifest.yaml`
- Create: `data/corpus/video-temporal-pose-summary.yaml`

- [ ] Select representative teaching windows for all 203 critical sources.
- [ ] Extract dense short sequences around selected timestamps.
- [ ] Run Pose over ordered sequences and compute public-safe geometry/visibility proxies.
- [ ] Record explicit blocked uses for racket face, shuttle contact, and true internal rotation.

### Task 5: Distillation And Explainability Chain

**Files:**
- Create: `scripts/build_multimodal_skill_evidence.py`
- Create: `skills/liu-hui-badminton-coach/references/multimodal-evidence-map.yaml`
- Modify: `skills/liu-hui-badminton-coach/references/full-corpus-synthesis.yaml`
- Modify: `skills/liu-hui-badminton-coach/references/reviewed-corpus-rules.yaml`
- Modify: `skills/liu-hui-badminton-coach/references/visual-evidence-contract.yaml`
- Modify: `skills/liu-hui-badminton-coach/SKILL.md`

- [ ] Map source/timestamp/visible evidence to frameworks and diagnostic questions.
- [ ] Strengthen only observable rule wording supported by the evidence level.
- [ ] Add report references that explain why a diagnosis was selected.
- [ ] Keep unsupported biomechanics as hypotheses or required observations.

### Task 6: Iterative Completion Audit

**Files:**
- Create: `scripts/audit_multimodal_completion.py`
- Create: `data/corpus/multimodal-completion-status.yaml`
- Modify: `README.md`
- Modify: `data/corpus/collection-status.md`
- Modify: `data/corpus/video-parse-status.md`

- [ ] Audit source, frame, VLM, Pose, temporal, explainability, and access-gap coverage.
- [ ] Generate retry work whenever any accessible item is incomplete.
- [ ] Run source integrity, examples, YAML parsing, compilation, and secret/raw-content scans.
- [ ] Review remaining gaps and repeat Tasks 2-6 until all completion gates pass.
- [ ] Commit and push the final verified state to `main`.
