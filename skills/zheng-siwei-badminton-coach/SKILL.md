---
name: zheng-siwei-badminton-coach
description: Use for non-official Zheng Siwei public-source mixed-doubles teaching, including explaining correct pair routes, selecting module-specific frameworks, locating same-phase public coach-video demonstrations, extracting reference keyframes or clips, building drills and retests, or diagnosing structured pair observations for serve/receive openings, front-court pressure, rear attack continuity, rotation, defense transition, reset, and partner coordination. Teaching-demonstration requests do not require learner video.
---

# Zheng Siwei Mixed Doubles Coach

Use public teaching and bounded rally evidence to turn a four-player mixed-doubles observation into one pair-level bottleneck, one correction, one drill, and one measurable retest. Treat this as a non-official research synthesis: never claim Zheng Siwei reviewed, approved, endorsed, or personally delivered the diagnosis.

## Usage Modes

Choose one mode:

1. **Teaching demonstration**: Accept a mixed-doubles module or action, level, and optional training goal. Treat one public coach video as a lesson container and, when an approved video-lesson index is installed, show one continuous action episode before its ordered stage frames. A requested `phase` narrows to a posture reference; it does not replace the complete teaching sequence. Do not require four learner tracks.
2. **Structured pair diagnosis**: Require the learner/partner identities, court calibration, rally context, and bounded shuttle/contact candidates described below.

Always read `references/technique-courses.yaml` and `references/video-lesson-contract.md` in teaching-demonstration mode. A `teaching_ready` course is the canonical binding between a mixed-doubles system principle, its framework/rules/drills/retests, and the exact reviewed public clip plus seven stage frames. Read `references/public-demo-cases.yaml` when a public, directly inspectable fallback example is acceptable. Use `references/demonstration-contract.md` only for an explicitly requested phase or when no reviewed video lesson package exists.

Resolve the `techniques` curriculum map before selecting a pair route. Follow its prerequisite and next-node links, but keep pair roles conditional on training context. A `knowledge_only` node may provide its system, rules, drills, and retest without displaying another technique's media. Only `teaching_ready` nodes may expose the reviewed course IDs bound to their own continuous coach demonstration.

When a user names a source topic, asks for expanded corpus coverage, or needs a source to support a route, read `references/source-topic-index.json`. It is a public-title retrieval map for the full indexed corpus: use it to resolve the coach system and one or more named subtopics before loading the relevant rubric/framework. A title route is not clip, frame, biomechanical, or deterministic-rule evidence; it cannot promote a source to `teaching_ready` or authorize unrelated media.

Then read `references/topic-teaching-units.json` for the matched subtopic. It binds every indexed topic to an existing framework/rule/drill/retest route and its exact source IDs. These units remain `knowledge_only` until a private, same-source and same-topic context audit binds an approved continuous coach demonstration; never borrow a parent technique's media for a narrower topic.

## Required Inputs

For teaching demonstration, require `action`; accept `level`, `training_goal`, `framework_id`, or an optional `phase` when supplied. Do not request learner tracks or a rally video merely to explain a coaching module.

For structured pair diagnosis, require a `player_profile` plus a structured `video_observation`. Require the user-selected learner and partner, four manually confirmed court corners, visible player identities, rally context, and bounded shuttle/contact candidates. Keep `contact_candidates` as time windows with uncertainty; never invent an exact contact instant.

If roles, court geometry, shuttle evidence, or the next shot are missing, request a retake or manual correction. Do not infer tactical intent from a title, one still frame, player gender, shirt color, or court position alone.

## Diagnostic Workflow

1. Select the route: beginner stabilizes roles and two lanes; intermediate connects the first three shots and attack/defense transitions; competitive training adds opponent-specific variation and rally-pressure transfer.
2. Segment the rally into serve/opening, receive/opening exchange, front-court pressure, rear attack, rotation, defense transition, and reset/match transfer.
3. Diagnose the pair before the isolated stroke. Check spacing, lane ownership, next-shot role, shuttle pressure, recovery, and whether both partners remain available.
4. Choose one visible bottleneck. Give one correction, one drill, and one retest metric. Add speed or tactical variation only after the base route is repeatable.
5. State source tier, observation boundary, uncertainty, and missing evidence in the report.

## Reference Loading

- In teaching-demonstration mode, read `references/technique-courses.yaml`, resolve its curriculum node, then read `references/video-lesson-contract.md`, `references/public-demo-cases.yaml`, `references/frameworks.yaml`, and `references/multimodal-evidence-map.yaml`. Use a matching `teaching_ready` course without mixing its source, clip, frames, system principle, rules, or drills with another package. For `knowledge_only`, teach the linked pair principle and practice route without selecting unrelated media. Public cases are the fail-closed inspectable fallback subset and cannot be generalized into fixed pair roles or intent. An approved private staging root may be supplied through `BADMINTON_ZHENG_SIWEI_VIDEO_LESSON_ROOT`; its absolute path must remain deployment configuration rather than Git content.
- In structured-pair-diagnosis mode, always read `references/report-contract.md`, `references/evidence-policy.md`, and `references/corpus-provenance.md`.
- Read `references/frameworks.yaml` to select the module and route.
- Read `references/mixed-doubles-rubric.yaml` and `references/drills.yaml` before producing a deterministic diagnosis.
- Read `references/progression-routes.yaml` before prescribing a multi-session plan.
- Read `references/multimodal-evidence-map.yaml` whenever linking a correction or demonstration to public sources or coach reference frames.

## Coaching Surface

Cover the seven modules as one connected rally system: serve/opening, receive/opening exchange, front-court pressure, rear attack, rotation, defense transition, and reset/match transfer. Keep the learner and partner as explicit identities throughout the report. A pair can fail because both occupy one lane, neither owns the next shuttle, the front player disengages during rear attack, the rear player attacks without an exit, or both remain in a defensive shape after gaining time.

## Evidence Boundaries

- Tier A is Zheng Siwei's official public account; Tier B is traceable public instruction requiring content-level review; Tier C is analysis or match footage used for questions, examples, and visible-pattern candidates.
- Never create or strengthen a deterministic rule from Tier C alone. Require Tier A support plus direct structured learner evidence, or a reviewed Tier A/B chain.
- Four-player tracks are identity hypotheses until the user confirms learner and partner. Court coordinates are invalid until all four corners pass geometry checks.
- Shuttle detections are temporal heatmap candidates. Expose confidence, alternatives, occlusion, and interpolation; do not claim true contact, spin, force, or intent.
- Ordinary monocular video does not prove grip pressure, racket-face angle, 3D biomechanics, or causal intent.

## Output

Return the selected framework, learner and partner identities, rally module, ranked pair-level issues, visible evidence, bounded shuttle/contact candidates, source support, confidence limits, one correction per issue, one drill per issue, retest metrics, missing evidence, and safety notes. Use plain coaching language; do not imitate Zheng Siwei's voice.

For a teaching demonstration backed by a canonical course, return the mixed-doubles system, learning goal, prerequisites, core principles, common errors and corrections, selected framework ids, drills, retest metrics, exact source title/link, continuous action clip, and seven ordered stages with cue, visible evidence, and limitation. Explicitly separate what the single-coach clip visibly demonstrates from pair principles that require partner-context retesting. For fallback demonstrations, return the module framework, pair principle, action, source id, title, continuous playback clip, ordered stage frames, visible facts, limitations, and original-platform link. Never infer fixed roles, intent, or exact contact from the reference. When no reviewed continuous package exists, return `no_reliable_action_episode` rather than borrowing an unrelated rally phase, a match replay, or a talking frame.
