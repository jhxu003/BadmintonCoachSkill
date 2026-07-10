# Video Parse Status

Updated: 2026-07-10

This file reports public-safe coverage and evidence boundaries. Raw media, transcripts, VLM output, Pose coordinates, model logs, cookies, and temporary URLs stay under ignored private storage.

## Source Accounting

| Item | Count |
|---|---:|
| Indexed Bilibili rows | 411 |
| Discovery-only rows | 2 |
| Independent video jobs | 409 |
| Accessible videos | 408 |
| Unavailable videos | 1 |
| Reviewed ASR sources | 408 |
| Visual action/demonstration sources | 402 |
| ASR-only conceptual/equipment sources | 6 |

Unavailable source: `LH_BILI_CORE_COMPETITION` / `corpus-370-lh_bili_core_competition`.

## ASR Timestamp Review

- Model: `mobiuslabsgmbh/faster-whisper-large-v3-turbo`.
- Audio scope: full audio.
- Reviewed teaching windows: 2610.
- ASR-topic-confirmed windows: 2535.
- Title-supported windows: 75.
- Missing accessible ASR sources: 0.

Top topic counts:

| Topic | Windows |
|---|---:|
| diagnosis_flow | 1453 |
| training_plan | 1253 |
| smash | 1192 |
| top_elbow | 1066 |
| student_fit | 1055 |
| internal_rotation | 852 |
| racket_preparation | 708 |
| high_clear | 672 |
| safety | 635 |
| wrist | 602 |
| hip_rotation | 439 |
| contact_point | 425 |
| match_transfer | 284 |
| footwork | 270 |
| drop | 262 |
| serve_receive | 136 |
| drive | 134 |
| doubles | 71 |
| equipment | 47 |

## Sparse Visual Layer

- Visual sources: 402.
- Planned teaching-window keyframes: 6064.
- VLM: `Qwen3-VL-8B-Instruct`, artifact version 4, schema `visible_still_frame_v2`.
- Pose: Ultralytics `yolo11n-pose.pt`, private coordinates with public-safe aggregates.
- Public visual summary: `video-visual-evidence-summary.yaml`.

Sparse VLM output describes visible still-frame conditions and routes reviewers to timestamps. It cannot independently establish motion, shuttle contact, force production, causality, racket-face geometry, grip pressure, or true joint rotation.

## Critical Temporal Layer

- Critical sources: 204.
- Dense sequences: 408.
- Dense frames: 5304.
- Public summary: `video-temporal-pose-summary.yaml`.

Dense Pose supports coarse monocular 2D body-geometry change and visibility checks. It still cannot establish calibrated 3D kinematics, racket or shuttle state, force, or true shoulder internal rotation.

## Explainability Layer

`skills/liu-hui-badminton-coach/references/multimodal-evidence-map.yaml` connects each accessible source to:

- reviewed ASR timestamps
- still-frame timestamps where visual scope exists
- temporal sequences for critical sources
- candidate framework ids
- diagnostic contracts
- evidence levels
- a confidence boundary

`multimodal-completion-status.yaml` is the machine-readable audit. The corpus is complete only when source accounting, visual artifacts, temporal artifacts, explainability, skill integration, publication safety, YAML integrity, and runtime behavior all pass.

## Platform Boundary

YouTube is excluded by project decision. Douyin and Instagram remain discovery-level access gaps and are not counted as parsed evidence.
