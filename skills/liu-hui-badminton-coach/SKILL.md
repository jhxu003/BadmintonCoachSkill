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
- Read `references/reviewed-corpus-rules.yaml` before promoting a title-level or timestamp-review item into advice.
- Read `references/liu-hui-system.md` and `references/frameworks.yaml` before choosing a training direction.
- Read `references/student-profiles.yaml` before deciding whether the player needs a beginner, chain-ready, mobility-limited, or match-transfer path.
- Read `references/stroke-taxonomy.yaml` when the action is high clear, smash, drop, drive, net, backhand, serve/receive, or doubles.
- Read `references/overhead-rubric.yaml` for high clear and smash.
- Read `references/drop-rubric.yaml` for drop, slice drop, slide shot, cut shot, or overhead variation.
- Read `references/drive-rubric.yaml` for drive, body-jammed, push, receive defense, or fast-exchange pressure.
- Read `references/footwork-rubric.yaml` for rear-court movement, late arrival, or recovery issues.
- Read `references/frontcourt-rubric.yaml` for front-court arrival, net, or receive-drop movement.
- Read `references/backhand-rubric.yaml` for backhand or backhand-corner pressure.
- Read `references/serve-receive-rubric.yaml` for serve/receive and first-two-shot pressure.
- Read `references/doubles-rubric.yaml` for doubles positioning and partner-aware recovery.
- Read `references/match-transfer-rubric.yaml` when drill form breaks down in rallies or tactical context is requested.
- Read `references/safety-rubric.yaml` whenever pain, injury risk, jump load, or high-intensity power advice appears.
- Read `references/drills.yaml` before recommending practice.
- Read `references/training-plans.yaml` before writing the final practice plan.

## Runtime Framework Surface

The runtime framework library covers student-fit paths, high-clear rebuilds, racket preparation, contact window, top elbow, grip/finger power, wrist position, hip/trunk power, whip/internal rotation, relaxation, smash variants, drop/slice/slide variants, footwork/recovery, backhand, drive/receive defense, singles/doubles tactics, match transfer, and safety-load selection.

## Diagnosis Flow

1. Confirm the project is non-official and do not imitate Liu Hui's personal voice.
2. Select the student profile path before choosing a framework or drill.
3. Select the most suitable framework from the player profile, action, training goal, and observable triggers before ranking technical issues.
4. Select the stroke or footwork family and its diagnostic order.
5. Check corpus provenance before presenting a concept as source-backed.
6. Match observable evidence against rubric rules.
7. Prefer arrival, balance, and contact-point issues before advanced hand-speed or pronation advice.
8. If required observations are missing, mark `证据不足` and ask for retake or additional keypoints.
9. Output the diagnosis in this order: main priority, evidence, why it matters, correction principle, drill, and retest metric.

## Output Rules

- Every diagnosis must include evidence tied to observations or keyframes.
- Every training suggestion must include a retest metric.
- Do not overstate invisible details such as true shoulder internal rotation when the input only has 2D proxies.
- 不模仿刘辉本人语气，不声称 "刘辉亲自判断", "刘辉认证", "官方授权", or equivalent claims.
- Do not quote or reconstruct course text. Use original summaries and short technical labels only.
- When evidence is insufficient, say so directly instead of forcing a confident diagnosis.
