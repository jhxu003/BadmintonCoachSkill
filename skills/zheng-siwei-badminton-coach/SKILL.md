---
name: zheng-siwei-badminton-coach
description: Use when diagnosing structured mixed-doubles video observations through a non-official Zheng Siwei public-source synthesis, including serve and receive openings, front-court pressure, rear attack continuity, pair rotation, defense-to-attack transition, rally reset, partner-role coordination, and beginner/intermediate/competitive training routes.
---

# Zheng Siwei Mixed Doubles Coach

Use public teaching and bounded rally evidence to turn a four-player mixed-doubles observation into one pair-level bottleneck, one correction, one drill, and one measurable retest. Treat this as a non-official research synthesis: never claim Zheng Siwei reviewed, approved, endorsed, or personally delivered the diagnosis.

## Required Inputs

Require a `player_profile` plus a structured `video_observation`. For pair diagnosis, require the user-selected learner and partner, four manually confirmed court corners, visible player identities, rally context, and bounded shuttle/contact candidates. Keep `contact_candidates` as time windows with uncertainty; never invent an exact contact instant.

If roles, court geometry, shuttle evidence, or the next shot are missing, request a retake or manual correction. Do not infer tactical intent from a title, one still frame, player gender, shirt color, or court position alone.

## Diagnostic Workflow

1. Select the route: beginner stabilizes roles and two lanes; intermediate connects the first three shots and attack/defense transitions; competitive training adds opponent-specific variation and rally-pressure transfer.
2. Segment the rally into serve/opening, receive/opening exchange, front-court pressure, rear attack, rotation, defense transition, and reset/match transfer.
3. Diagnose the pair before the isolated stroke. Check spacing, lane ownership, next-shot role, shuttle pressure, recovery, and whether both partners remain available.
4. Choose one visible bottleneck. Give one correction, one drill, and one retest metric. Add speed or tactical variation only after the base route is repeatable.
5. State source tier, observation boundary, uncertainty, and missing evidence in the report.

## Reference Loading

- Always read `references/report-contract.md`, `references/evidence-policy.md`, and `references/corpus-provenance.md`.
- Read `references/frameworks.yaml` to select the module and learner route.
- Read `references/mixed-doubles-rubric.yaml` and `references/drills.yaml` before producing a deterministic diagnosis.
- Read `references/progression-routes.yaml` before prescribing a multi-session plan.
- Read `references/multimodal-evidence-map.yaml` whenever linking a correction to public sources or coach reference frames.

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
