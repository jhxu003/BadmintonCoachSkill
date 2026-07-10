# Full Multimodal Liu Hui Corpus Design

## Goal

Complete the accessible non-YouTube Liu Hui public corpus at teaching-window level, not only at title or ASR level. Every action-bearing source must end in one of two auditable states: successfully processed with public-safe visual evidence, or unavailable with a concrete access failure.

## Completion Contract

The project is complete only when all of the following are true:

1. All 396 action-bearing sources in `video-visual-review-manifest.yaml` have a terminal visual status.
2. All 5977 planned teaching-window frames have extraction and model-processing status.
3. Every successfully accessible action source has VLM visibility evidence and Pose coverage.
4. The 203 critical sources have denser temporal evidence around representative teaching windows.
5. Public evidence links source id, timestamp, visible observation class, confidence boundary, and applicable Skill framework without exposing raw model text or coordinates.
6. Skill rules distinguish ASR routing evidence, sampled visual evidence, temporal Pose proxies, and human-reviewed evidence.
7. Raw video, audio, frames, transcripts, model output, and keypoint coordinates remain private.
8. Coverage, source integrity, runtime examples, YAML parsing, compilation, and publication-safety checks pass.

## Architecture

### Exact Visual Manifest Execution

Create a pipeline manifest by joining the 396 visual-review jobs to their original pilot/corpus job definitions. Add a `visual-review` keyframe source that consumes each job's exact `planned_frames` instead of resampling ASR windows. The extraction manifest records every requested timestamp and every extraction failure.

### Structured VLM Evidence

Run Qwen2.5-VL-3B over the ordered teaching-window frames. Private output retains the model response. Public distillation exposes only timestamped visibility categories, coverage counts, and evidence limitations. The model may identify visible racket preparation, body organization, contact/pre-contact candidates, lower-body orientation, recovery, and on-screen text presence; it may not assert invisible biomechanics or coaching intent.

### Pose And Temporal Proxies

Run YOLO pose over all planned frames and retain private keypoints. For critical sources, create denser samples around selected teaching timestamps and calculate coarse phase-to-phase body geometry. These are visibility and sequence proxies, not proof of racket orientation, shuttle contact, or true shoulder internal rotation.

### Skill Distillation

Aggregate visual and temporal evidence by source, topic, and framework. Promote only claims whose evidence level permits the wording. Every promoted or strengthened rule must carry source ids, timestamp pointers, visible observation requirements, and blocked interpretations.

## Compute Strategy

Use node-local `/tmp` for environments, model checkpoints, videos, frames, and raw model outputs. Use a healthy compute node with sufficient free GPU memory. Split the 396-job manifest into resumable shards. Copy back only JSON logs and artifacts after each shard, then rebuild public summaries on the shared repository.

## Failure Policy

A model process returning exit code zero is not sufficient. Completion checks inspect each stage status. Failed downloads, missing frames, invalid VLM output, and missing Pose artifacts enter retry manifests. A source becomes unavailable only after bounded retries record a stable access failure.

## Non-Goals And Boundaries

- YouTube remains excluded by project decision.
- Paid, private, deleted, or inaccessible material is not reconstructed.
- Model evidence is not called human review.
- The project does not claim official Liu Hui authorization or endorsement.
