---
name: li-yuxuan-badminton-coach
description: Use when turning structured badminton player profiles and video observations into evidence-grounded Li Yuxuan coaching diagnosis for high clear, smash, drop, drive, footwork, backhand, serve/receive, doubles, training progression, equipment fit, and load-aware practice.
---

# Li Yuxuan Badminton Coach Skill

This is a non-official public-source research synthesis. It provides an evidence-bounded diagnostic and training workflow informed by publicly accessible Li Yuxuan teaching material. It must not claim that Li Yuxuan reviewed, approved, endorsed, or personally delivered a diagnosis.

## Required Inputs

Use this Skill after a video agent or a human annotator has supplied a `player_profile` and a `video_observation` that includes the action, camera view, visible phases, contact proxy, preparation frame, release sequence proxy, footwork, recovery, missing observations, and keyframes.

When raw video is the only input, request structured observations or run a video-analysis agent first. Do not convert a title, an isolated still, or a model-generated description into a biomechanical fact.

## Diagnostic Order

1. Select the player-fit route. Check level, coordination, mobility, injury risk, available practice time, and the target ball effect.
2. Establish the time budget. For an overhead or movement problem, inspect opponent-contact start cue, first step, arrival, confirmation step, contact window, and recovery before arm speed.
3. Choose one bottleneck. Make one correction, pair it with one drill and one retest metric, then add speed, variation, jump load, or rally pressure.
4. Build the report around visible evidence. Separate source-supported teaching direction, 2D visual proxy, diagnosis hypothesis, and missing evidence.

## Reference Loading

- Always read `references/report-contract.md`, `references/corpus-provenance.md`, and `references/visual-evidence-contract.yaml`.
- Read `references/frameworks.yaml` before choosing the primary route and `references/student-profiles.yaml` before giving a progression path.
- Read `references/stroke-taxonomy.yaml` for action-specific diagnostic order.
- Read `references/overhead-rubric.yaml` for high clear, smash, drop, top elbow, turn, release, or internal-rotation proxy questions.
- Read `references/footwork-rubric.yaml` for starting, rear/front movement, ready-racket, landing, recovery, and match-transfer questions.
- Read `references/serve-receive-rubric.yaml` for serve, receive, doubles roles, and the first two shots.
- Read `references/safety-rubric.yaml` when pain, equipment, footwear, floor condition, or jump load appears.
- Read `references/drills.yaml` and `references/training-plans.yaml` before writing practice.
- Read `references/multimodal-evidence-map.yaml` whenever a report links a recommendation to the public corpus.

## Coaching Surface

The Skill covers learner-fit framework selection, high clear, rear-court turn and confirmation step, smash and jump-smash prerequisites, overhead variation, compact drive, front-court and receive response, doubles first-two-shot roles, backhand time budget, practice-to-rally transfer, equipment maturity, and shoe/floor/ankle safety.

Its central diagnostic rule is that a visible late start or late arrival must be resolved before assigning a hand, wrist, elbow, or power correction. For overhead power, it stages preparation, contact, turn-to-arm timing, release, landing, and recovery rather than prescribing an isolated movement.

## Evidence Boundaries

- `source_backed` and `inferred` refer to the public-source synthesis, not an official coaching endorsement.
- VLM still-frame output is a timestamped visibility candidate, not proof of stroke phase, force, intent, or causality.
- Dense 2D pose is a coarse geometry proxy, not motion capture.
- Never claim true shoulder internal rotation, force, grip pressure, racket-face angle, shuttle contact, or calibrated 3D biomechanics from ordinary monocular video.
- When a required view or phase is missing, state what must be recorded rather than filling the gap with a confident diagnosis.

## Report Requirements

Every report must include the selected framework, ranked issue list, observable evidence, confidence and limitations, one correction principle per issue, one drill per issue, a measurable retest, safety notes, and a request for missing views where needed. Advice about pain must be conservative and must not substitute for medical assessment.
