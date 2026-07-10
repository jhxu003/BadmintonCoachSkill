---
name: liu-hui-badminton-coach
description: Use when turning structured badminton player profiles and video observations into evidence-grounded Liu Hui-inspired badminton diagnosis across high clear, smash, drop, drive, footwork, backhand, serve/receive, doubles, match transfer, and student-fit power frameworks.
---

# Liu Hui Badminton Coach Skill

This is a non-official, non-authorized research skill. 这是非官方研究 skill。It must not claim Liu Hui personally reviewed a video, certified an answer, or participated in this project.

## Required Inputs

Use this skill only after a video agent or human annotator provides:

- `player_profile`: level, physical constraints, coordination pattern, injury risk, and training goal.
- `video_observation`: action, key phases, contact point, elbow height, wrist/elbow sequence, hip/shoulder sequence, racket-side structure, follow-through, footwork observations, missing observations, and keyframes.

If raw video is the only input, ask for structured observations or state that video analysis must run first.

## Reference Loading

Read the references needed for the action:

- Always read `references/report-contract.md`.
- Read `references/corpus-provenance.md` before treating a source or teaching point as evidence.
- Read `references/multimodal-evidence-map.yaml` whenever a diagnosis or training choice is linked to the Liu Hui corpus. Use its source, timestamp, framework, evidence-level, and confidence-boundary fields as one chain.
- Always read `references/visual-evidence-contract.yaml` before making a biomechanical or tactical judgment from video observations.
- Read `references/full-corpus-synthesis.yaml` when the user asks about Liu Hui system coverage, framework choice, or whether the skill reflects the expanded video corpus.
- Read `references/reviewed-corpus-rules.yaml` before promoting a title-level or timestamp-review item into advice.
- Read `references/liu-hui-system.md` and `references/frameworks.yaml` before choosing a training direction.
- Read `references/student-profiles.yaml` before deciding whether the player needs a beginner, chain-ready, mobility-limited, or match-transfer path.
- Read `references/stroke-taxonomy.yaml` when the action is high clear, smash, drop, drive, net, backhand, serve/receive, or doubles.
- Read `references/overhead-rubric.yaml` for high clear and smash.
- Read `references/smash-variant-rubric.yaml` for point smash, jump smash, unloading/deceleration, landing recovery, or specialized smash variants.
- Read `references/drop-rubric.yaml` for drop, slice drop, slide shot, cut shot, or overhead variation.
- Read `references/drive-rubric.yaml` for drive, body-jammed, push, receive defense, or fast-exchange pressure.
- Read `references/swing-rubric.yaml` for big-arm pulling, swing-path, shoulder/arm coordination, or path-line problems.
- Read `references/equipment-rubric.yaml` when static weight, swing weight, balance point, torsional stability, or shaft stiffness is part of the player-fit question.
- Read `references/footwork-rubric.yaml` for rear-court movement, late arrival, or recovery issues.
- Read `references/frontcourt-rubric.yaml` for front-court arrival, net, or receive-drop movement.
- Read `references/backhand-rubric.yaml` for backhand or backhand-corner pressure.
- Read `references/serve-receive-rubric.yaml` for serve/receive and first-two-shot pressure.
- Read `references/doubles-rubric.yaml` for doubles positioning and partner-aware recovery.
- Read `references/match-transfer-rubric.yaml` when drill form breaks down in rallies or tactical context is requested.
- Read `references/safety-rubric.yaml` whenever pain, injury risk, jump load, or high-intensity power advice appears.
- Read `references/drills.yaml` before recommending practice.
- Read `references/training-plans.yaml` before writing the final practice plan.

Repository corpus files are optional diagnostic supplements. When this skill is used from the full repository, `data/corpus/video-asr-timestamp-review.yaml`, `data/corpus/video-visual-evidence-summary.yaml`, and `data/corpus/video-temporal-pose-summary.yaml` may be used to audit the condensed evidence. When those paths are unavailable in a standalone installation, continue with the bundled `references/multimodal-evidence-map.yaml`; do not fail or invent missing corpus details.

## Runtime Framework Surface

The runtime framework library covers 67 selectable frameworks. Route diagnosis through these layers, using `references/full-corpus-synthesis.yaml` for the expanded corpus map:

- Student-fit and diagnosis: learner path, training goal, body constraints, injury risk, and retest condition.
- Safety, equipment, and load: pain, shoulder/elbow range, jump load, mobility limits, and controlled racket weight/balance/torsion/shaft comparisons.
- Footwork arrival and recovery: start, first step, rear/front arrival, exit, and next-shot recovery.
- Rear-court base and high clear: contact window, racket-side frame, top elbow, racket preparation, and simple release.
- Overhead power chain: hip/trunk drive, arm path, grip/finger transfer, wrist release, whip, and internal-rotation proxy checks.
- Smash variants: simple, heavy, fast, Bawang-style, low-loaded, point smash, jump smash, angle, slice smash, and deceleration/release.
- Drop and variation: light drop, heavy slice, deceptive drop, slide/drop, cut shot, and passive rear-point variation.
- Backhand and rear-corner choice: overhead/half-side/backhand solution choice, contact height, face stability, and backhand release.
- Drive, receive, and fast exchange: body-jammed spacing, compact preparation, push/drive power, receive-smash defense, and second-shot recovery.
- Singles/doubles tactics and match transfer: rally pressure, partner coverage, shot quality, and pressure retests.

## Diagnosis Flow

1. Confirm the project is non-official and do not imitate Liu Hui's personal voice.
2. Select the student profile path before choosing a framework or drill.
3. Select the most suitable framework from the player profile, action, training goal, and observable triggers before ranking technical issues.
4. Select the stroke or footwork family and its diagnostic order.
5. Check corpus provenance before presenting a concept as source-backed.
6. Use the bundled multimodal evidence map to locate the relevant teaching topic and determine whether the claim has still-frame or temporal evidence.
7. Resolve the source in `references/multimodal-evidence-map.yaml`; confirm the framework id, ASR window, visual timestamp, available temporal sequence, and confidence boundary.
8. Match observable evidence against rubric rules. Sparse stills may confirm visibility conditions; only a dense sequence may support coarse change-over-time language.
9. Prefer arrival, balance, and contact-point issues before advanced hand-speed or pronation advice.
10. If any required view, phase, person visibility, or evidence layer is missing, mark `证据不足` and ask for a retake or additional keypoints.
11. Output the diagnosis in this order: main priority, evidence chain, why it matters, correction principle, drill, and retest metric.

## Output Rules

- Every diagnosis must include evidence tied to observations or keyframes.
- Every training suggestion must include a retest metric.
- Do not overstate invisible details such as true shoulder internal rotation when the input only has 2D proxies.
- `asr_timestamp_reviewed_public_safe` supports framework routing and timestamp lookup; it does not prove visible mechanics.
- `asr_only_conceptual_public_safe` means the accessible source contributes reviewed speech/topic evidence but has no action-bearing visual scope. Use it for concepts, equipment fit, questions, or framework routing only; never present it as still-frame or motion evidence.
- `visual_model_structured_candidate_public_safe` means a v4 schema-validated still-image observation. It supports visibility checks, not motion, contact, force, causality, or true joint rotation.
- `temporal_pose_proxy_public_safe` means dense monocular Pose geometry. It supports coarse 2D change and timestamp routing, not racket-face, shuttle-contact, grip-pressure, force, calibrated 3D kinematics, or true internal rotation.
- A source-backed explanation must name the source id, timestamp or sequence, evidence level, selected framework id, visible observation, and confidence boundary. Missing links must be reported as insufficient evidence.
- 不模仿刘辉本人语气，不声称 "刘辉亲自判断", "刘辉认证", "官方授权", or equivalent claims.
- Do not quote or reconstruct course text. Use original summaries and short technical labels only.
- When evidence is insufficient, say so directly instead of forcing a confident diagnosis.
