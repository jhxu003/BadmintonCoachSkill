---
name: li-yuxuan-badminton-coach
description: Use for evidence-grounded Li Yuxuan public-source badminton teaching, including explaining correct action progressions, selecting time-budget and learner-fit frameworks, locating same-phase coach-video demonstrations, extracting reference keyframes or clips, creating drills and retests, or diagnosing structured observations for high clear, smash, drop, drive, footwork, backhand, serve/receive, doubles, equipment, and load-aware practice. Teaching-demonstration requests do not require learner video.
---

# Li Yuxuan Badminton Coach Skill

This is a non-official public-source research synthesis. It provides an evidence-bounded diagnostic and training workflow informed by publicly accessible Li Yuxuan teaching material. It must not claim that Li Yuxuan reviewed, approved, endorsed, or personally delivered a diagnosis.

## Usage Modes

Choose one mode:

1. **Teaching demonstration**: Accept an action, learning level, and optional training goal. When a reviewed video lesson exists, first show its continuous coach-action episode and then its ordered nine-stage navigation with teaching text; a source video may teach several actions. Accept `phase` only for an explicitly targeted posture reference. Do not infer a learner fault.
2. **Structured diagnosis**: Accept a player profile and structured observation, resolve the time budget and visible bottleneck, then return one correction, drill, and retest.

Always read `references/technique-courses.yaml` and `references/video-lesson-contract.md` in teaching-demonstration mode. A `teaching_ready` course is the canonical binding between the Li Yuxuan progression, its framework/rules/drills/retests, and the exact reviewed public clip plus seven stage frames. Read `references/public-demo-cases.yaml` when a public, directly inspectable fallback example is acceptable. Read `references/demonstration-contract.md` only for an explicitly requested phase or when no reviewed continuous lesson package exists.

Resolve the `techniques` curriculum map before selecting a lesson. Follow its prerequisites and next nodes for the requested level. A `knowledge_only` node may teach its linked system, framework, rule, drill, and retest, but cannot display a clip or frame from a different technique. Only `teaching_ready` nodes may expose their own bound course media.

## Required Inputs

For teaching demonstration, require `action`. Accept `level`, `training_goal`, or `framework_id` when supplied. Require `phase` only for a targeted same-phase lookup. Do not request learner video solely to show or explain the coach's action.

For structured diagnosis, use diagnosis mode after a video agent or a human annotator has supplied a `player_profile` and a `video_observation` that includes the action, camera view, visible phases, contact proxy, preparation frame, release sequence proxy, footwork, recovery, missing observations, and keyframes.

When raw learner video is the only diagnostic input, request structured observations or run a video-analysis agent first. Do not convert a title, an isolated still, or a model-generated description into a biomechanical fact. This restriction does not block teaching-demonstration mode.

## Diagnostic Order

1. Select the player-fit route. Check level, coordination, mobility, injury risk, available practice time, and the target ball effect.
2. Establish the time budget. For an overhead or movement problem, inspect opponent-contact start cue, first step, arrival, confirmation step, contact window, and recovery before arm speed.
3. Choose one bottleneck. Make one correction, pair it with one drill and one retest metric, then add speed, variation, jump load, or rally pressure.
4. Build the report around visible evidence. Separate source-supported teaching direction, 2D visual proxy, diagnosis hypothesis, and missing evidence.

## Reference Loading

- In teaching-demonstration mode, read `references/technique-courses.yaml`, resolve its curriculum node, then read `references/video-lesson-contract.md`, `references/public-demo-cases.yaml`, and `references/frameworks.yaml`. Use a matching `teaching_ready` course without mixing its source, clip, frames, principles, rules, or drills with another package. For `knowledge_only`, return only the route, principles, drills, and retest; do not substitute a public case from a different technique. Public cases are the fail-closed inspectable fallback subset; quarantined entries must never be selected. Use the title plus reviewed ASR index to identify the lesson topic; use VLM only for strict action gating. An approved private staging root may be supplied at runtime through `BADMINTON_LI_YUXUAN_VIDEO_LESSON_ROOT`; its absolute path must remain deployment configuration rather than Git content. Read `references/demonstration-contract.md` only for an explicitly requested phase or when no reviewed video lesson package exists.
- In structured-diagnosis mode, always read `references/report-contract.md`, `references/corpus-provenance.md`, and `references/visual-evidence-contract.yaml`.
- Read `references/frameworks.yaml` before choosing the primary route and `references/student-profiles.yaml` before giving a diagnosis progression path.
- Read `references/stroke-taxonomy.yaml` for action-specific diagnostic order.
- Read `references/overhead-rubric.yaml` for high clear, smash, drop, top elbow, turn, release, or internal-rotation proxy questions.
- Read `references/footwork-rubric.yaml` for starting, rear/front movement, ready-racket, landing, recovery, and match-transfer questions.
- Read `references/serve-receive-rubric.yaml` for serve, receive, doubles roles, and the first two shots.
- Read `references/safety-rubric.yaml` when pain, equipment, footwear, floor condition, or jump load appears.
- Read `references/drills.yaml` and `references/training-plans.yaml` before writing practice.
- Read `references/multimodal-evidence-map.yaml` whenever a report links a recommendation or demonstration to the public corpus.
- Use `asr_timestamp_reviewed_public_safe` for reviewed topic routing and timestamp lookup.
- Use `asr_only_conceptual_public_safe` only for conceptual routing when no action-bearing visual review exists.
- Use `visual_model_structured_candidate_public_safe` only for schema-validated visible still-frame conditions.
- Use `temporal_pose_proxy_public_safe` only for coarse, bounded 2D change across a reviewed sequence.

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

For a teaching demonstration backed by a canonical course, return the system, learning goal, prerequisites, core principles, common errors and corrections, selected framework ids, drills, retest metrics, exact source title/link, continuous action boundary and clip, and seven ordered stages with cue, visible evidence, and limitation. For a fallback lesson, return the selected framework, lesson topic, controlled action, source id, continuous action and playback boundaries, clip availability, and ordered stage list. A still is posture navigation, not proof of complete motion. For an explicitly requested phase, use only a same-phase reference; return `no_reliable_same_phase_demonstration_frame` instead of substituting another phase. If no reviewed continuous episode exists, return `no_reliable_action_episode` rather than a speech or gesture frame.
