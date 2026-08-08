---
name: liu-hui-badminton-coach
description: Use for evidence-grounded Liu Hui-inspired badminton teaching, including explaining correct action principles, selecting learner-fit frameworks, locating same-phase public coach-video demonstrations, extracting reference keyframes or clips, building drills and retests, or diagnosing structured player observations across high clear, smash, drop, drive, footwork, backhand, serve/receive, doubles, equipment, and match transfer. Teaching-demonstration requests do not require learner video.
---

# Liu Hui Badminton Coach Skill

This is a non-official, non-authorized research skill. 这是非官方研究 skill。It must not claim Liu Hui personally reviewed a video, certified an answer, or participated in this project.

## Usage Modes

Choose one mode before loading detailed references:

1. **Teaching demonstration**: Accept an action, learning level, and teaching goal. Treat one public coach video as a lesson container that may cover several techniques. Resolve and display its complete reviewed technique inventory before selecting one or more technique packages. For each requested technique, show a continuous pure-action episode before 7–9 ordered stage frames; attach an action point and evidence boundary to every frame. Accept `phase` only when the user explicitly asks for one targeted posture reference. Do not require learner video or invent a learner problem.
2. **Structured diagnosis**: Accept a player profile plus structured observations from a human or video agent. Rank one observable bottleneck and bind it to teaching, practice, and retest evidence.

Always read `references/technique-courses.yaml` and `references/video-lesson-contract.md` in teaching-demonstration mode. Treat a `teaching_ready` technique course as the canonical knowledge-media binding: it resolves the system, framework, common-error rules, drills, retest metrics, exact source, reviewed continuous clip, and seven stage frames together. When no matching technique course exists, use `references/video-lessons-index.yaml` to select the relevant family shard under `references/video-lessons/`, or fall back to `references/video-lessons.yaml`. In the local runtime, an approved private staging root may instead be supplied through `BADMINTON_VIDEO_LESSON_ROOT`; it must contain that index and its `video-lessons/` shards, and its absolute path must remain deployment configuration rather than Git content. Read `references/demonstration-contract.md` as the fallback contract for an explicitly requested phase or when no reviewed video lesson package exists.

Resolve the `techniques` curriculum map before choosing a teaching route. Follow its prerequisites and next nodes at the learner's level. A `knowledge_only` node may supply its linked system, principles, rules, drills, and retest, but must never borrow an unrelated clip or frame. Only a `teaching_ready` node may show the course IDs bound to its own reviewed continuous media.

When a user names a source topic, asks for expanded corpus coverage, or needs a source to support a route, read `references/source-topic-index.json`. It is a public-title retrieval map for the full indexed corpus: use it to resolve the coach system and one or more named subtopics before loading the relevant rubric/framework. A title route is not clip, frame, biomechanical, or deterministic-rule evidence; it cannot promote a source to `teaching_ready` or authorize unrelated media.

Then read `references/topic-teaching-units.json` for the matched subtopic. It binds every indexed topic to an existing framework/rule/drill/retest route and its exact source IDs. These units remain `knowledge_only` until a private, same-source and same-topic context audit binds an approved continuous coach demonstration; never borrow a parent technique's media for a narrower topic.

## Required Inputs

For teaching demonstration, require:

- `action`: the stroke, footwork, tactical, or equipment topic.
- Optional `level`, `training_goal`, or `framework_id` to select a narrower route.
- Optional `phase`: preparation, start, arrival, top elbow, contact window, follow-through, or recovery, only for a targeted phase lookup.

Do not request learner video when these inputs are sufficient.

For structured diagnosis, use diagnosis mode only after a video agent or human annotator provides:

- `player_profile`: level, physical constraints, coordination pattern, injury risk, and training goal.
- `video_observation`: action, key phases, contact point, elbow height, wrist/elbow sequence, hip/shoulder sequence, racket-side structure, follow-through, footwork observations, missing observations, and keyframes.

If raw learner video is the only diagnostic input, ask for structured observations or state that video analysis must run first. This restriction does not apply to teaching-demonstration requests.

## Reference Loading

Load references by mode and action:

- In teaching-demonstration mode, first read `references/technique-courses.yaml`, resolve the curriculum node and its route, then read `references/video-lesson-contract.md` and `references/frameworks.yaml`. If that node is `teaching_ready`, use its complete knowledge-media package without substituting another source, clip, stage image, framework, rule, or drill. If it is `knowledge_only`, teach its principles, drills, and retest without displaying unrelated media. Otherwise inspect the installed video-lesson index or catalog. Build a source video's full technique inventory before frame selection: use the public title and reviewed ASR topic indexes to route each lesson topic, action, family, taxonomy path, and semantic interval; use VLM action windows only for strict action gating and visual compatibility. Prefer `agent_reviewed` packages, exclude speech and isolated racket gestures from storyboards, and keep every displayed stage inside its one continuous episode.
- Before treating any episode as a reliable teaching demonstration, review at least 20 seconds before and 20 seconds after the action and require `demonstrator_role=coach`, `example_polarity=correct`, and `context_review_status=agent_reviewed`. A visually complete learner attempt, a correction-in-progress repetition, or a coach intentionally showing an error must fail closed and stay out of learner-facing keyframes.
- For an explicitly requested phase or when no reviewed lesson package exists, read `references/demonstration-contract.md` and `references/reviewed-demonstrations.yaml`. Prefer an `agent_reviewed` same-phase timepoint over a model-only candidate.
- In structured-diagnosis mode, always read `references/report-contract.md` and `references/visual-evidence-contract.yaml`.
- Read `references/corpus-provenance.md` before treating a source or teaching point as evidence.
- Read `references/multimodal-evidence-map.yaml` whenever a diagnosis, training choice, or demonstration is linked to the Liu Hui corpus. Use its source, timestamp, framework, evidence-level, and confidence-boundary fields as one chain.
- Read `references/full-corpus-synthesis.yaml` when the user asks about Liu Hui system coverage, framework choice, or whether the skill reflects the expanded video corpus.
- Read `references/reviewed-corpus-rules.yaml` before promoting a title-level or timestamp-review item into advice.
- Read `references/liu-hui-system.md` and `references/frameworks.yaml` before choosing a diagnosis training direction.
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

For an explicitly owner-approved public lesson sample, use the repository-wide `scripts/export_public_lesson.py` to export one reviewed continuous episode as browser-safe H.264 plus exactly seven ordered JPEG stage frames. Supply absolute source timestamps and an agent-reviewed JSON manifest proving coach identity, correct-example polarity, and a surrounding context interval. Keep every frame inside the clip window, retain source attribution and the public window beside the assets, and keep the original video outside Git. Do not publish coach media merely because it exists in the private runtime; require explicit publication permission for each public asset set.

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

- In teaching-demonstration mode, first output the source video's reviewed technique inventory. For a matching canonical technique course, output its system, learning goal, prerequisites, core principles, common errors and corrections, resolved framework ids, drills, retest metrics, exact source title/link, reviewed action boundary, continuous clip, and seven ordered stages with cue, visible evidence, and limitation. For non-course fallback packages, output the lesson topic, controlled action, technique family, taxonomy path, semantic review status, selected framework, package completeness, concise teaching summary, source id, full episode boundary, continuous clip availability, ordered stages, a teaching point and evidence boundary for every stage frame, visible facts, limitations, and original-platform jump link.
- Do not reduce a video lesson to `demonstration` versus `talking`. Motion gating only decides which windows deserve action expansion; it does not identify the taught technique or technical system.
- Do not populate a technique storyboard with talking, pointing, shuttle throwing without a racket stroke, grip adjustment, racket-face placement, isolated wrist or forearm rotation, or held poses. If a reviewed technique has no reliable action episode, say so and preserve the gap.
- Do not auto-promote a model-labeled partial demonstration. Automatic batch admission requires one high-confidence, high-purity, single continuous repetition with a full visible trajectory and at least four visible stage codes; otherwise preserve it only in the private review workspace.
- Do not quote or reconstruct course transcripts or on-screen subtitles. Use reviewed topic indexes and original short summaries.
- Present each continuous episode before its 7–9-frame stage storyboard. Keep the action boundary and every stage frame inside one repetition. Label a separate playback boundary when the clip retains 1–2 seconds after the action to show shuttle flight or landing; end that result segment before the next stroke. Do not concatenate stages from different repetitions or use stills from another technique.
- Treat a keyframe as posture navigation and a short clip as process context. Never present one frame as the whole correct technique.
- Use only an action-compatible, same-phase reference. If no reliable reference exists, return `no_reliable_same_phase_demonstration_frame`; do not borrow another phase.
- Label model-located public frames as demonstration references, not official certification or independent proof that every visible detail is correct.

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
