# Liu Hui-Inspired Coaching System

This file stores original, research-oriented summaries derived from public source indexing. It is not an official Liu Hui document.

## Corpus Status

The current runtime system is complete against the accessible non-YouTube public Bilibili index in this repository, not an official Liu Hui archive. YouTube is excluded by project decision. Douyin and Instagram remain explicit access gaps because stable public per-video metadata or media access is unavailable.

The video-content pilot processed 30 indexed public Bilibili teaching videos. The expanded Bilibili ASR pass processed 378 of 379 corpus jobs with full-audio `mobiuslabsgmbh/faster-whisper-large-v3-turbo`; one public page now resolves to a missing-video placeholder. The combined pass produced 2567 public-safe timestamp candidates across 401 sources. Every candidate was then checked against its private ASR interval and emitted as an original public-safe timestamp review in `data/corpus/video-asr-timestamp-review.yaml`: 2567 reviewed windows, 401 reviewed sources, zero missing manifest jobs, and zero missing ASR artifacts behind those windows.

The visual completion layer maps 396 action-bearing sources to 5977 planned teaching-window keyframes and marks 5 conceptual sources as ASR-only. Existing private VLM output covers 30 pilot sources and 336 keyframes; `data/corpus/video-visual-evidence-summary.yaml` exposes only timestamps and visibility counts. Pose and VLM evidence remain model candidates until a human reviews the referenced frames.

`references/full-corpus-synthesis.yaml` is the current complete system map for the indexed public corpus. It organizes the expanded evidence into student-fit diagnosis, safety/equipment/load, footwork arrival/recovery, rear-court base, overhead power chain, smash variants, drop/slide variation, backhand/rear-corner choice, drive/receive exchange, and singles/doubles match transfer. Treat it as the runtime routing layer before reading the narrower rubrics.

`references/visual-evidence-contract.yaml` is the explainability gate. It defines the camera view, visible phases, allowed claims, blocked claims, and retake request for arrival/contact, top elbow, hip/trunk timing, internal-rotation proxies, grip/wrist/racket face, footwork, drop geometry, fast exchange, doubles continuity, and safety/load.

## Working Hypothesis

The distinctive coaching value to model is not a single "standard swing." It is the ability to choose a power framework, correction order, and training path that fit the student's current body, coordination, and goal.

## Core Principles

- Fit the framework to the student before giving drills.
- Solve arrival and contact point before asking for faster whip or pronation.
- Build racket-side structure before adding speed.
- Treat top elbow as a frame and sequencing problem, not an isolated arm cue.
- Treat internal rotation/pronation as a consequence of a usable kinetic chain and racket path, not a forced wrist twist.
- Keep advice staged: one priority now, one drill, one retest metric.
- Separate source-backed teaching points from inferred synthesis and third-party discussion.

## Runtime Framework Catalog

`frameworks.yaml` contains the selectable diagnosis surface. It is intentionally broader than a few named strokes:

- Student-fit paths: learning order, match transfer, mobility/safety, equipment fit.
- Rear-court base: stable overhead, high-clear base power, action-change sequence, contact window, top elbow.
- Racket and release: static frame, standard preparation, racket-face control, wrist position, grip/finger power, arm path, unloading/deceleration.
- Power systems: hip/trunk chain, whip release, internal rotation, concentrated power, flash power, relaxation, tension observation, non-racket-side balance, shoulder range.
- Smash systems: simple smash, angle/downward pressure, heavy smash, fast smash, Bawang smash, low-loaded smash, point smash, jump smash contact/landing, slice/cut smash.
- Variation systems: light drop, heavy slice drop, deceptive drop, slide/drop, cut shot.
- Movement systems: passive rear transition, half-side attack, rear-corner choice, start/recovery, lazy-legs recovery, front-court arrival, elastic footwork.
- Backhand systems: passive backhand, backhand-corner choice, backhand whip.
- Fast-exchange systems: body-jammed drive, push/drive power, receive-smash defense, high serve and first-shot, compact front-court receive.
- Match systems: doubles rear continuity, doubles fast exchange, singles tactical core, tactical observation.
- Timestamp-candidate systems: time-budget preparation, compact standard frame, frame tradeoff selector, foot-ground hip drive, arm-segment transfer, drop/slide variant selection, China-jump recovery, and wrist contact-transfer.

## Video Pilot Distillation

`data/corpus/video-asr-teaching-windows.yaml` stores curated pilot candidate windows. `data/corpus/video-asr-teaching-windows-full.yaml` stores expanded candidate windows. `data/corpus/video-asr-timestamp-review.yaml` stores the complete public-safe agent review of those windows. `data/corpus/video-visual-review-manifest.yaml` defines visual review coverage, while VLM and pose summary files expose only safe aggregate evidence. Raw ASR text, audio, video, OCR, VLM outputs, keypoint coordinates, cookies, tokens, temporary media URLs, and paid-course material must stay private.

Use reviewed timestamp material as follows:

- It may guide framework routing, observation requests, drill choice, and human-review queues.
- It may be cited by `evidence_ids` for internal traceability.
- It must not be described as Liu Hui's exact words or as human-reviewed evidence.
- Visible mechanics such as contact point, top elbow, hip timing, racket face, and internal rotation still require direct video frames.
- It must not override earlier observable layers such as arrival, contact point, frame, elbow sequence, and safety.
## Priority Heuristic

1. Can the player arrive in time and stay balanced?
2. Is contact in a playable front-high window?
3. Is the racket-side frame stable enough to transfer force?
4. Does elbow lead before wrist acceleration?
5. Does hip/trunk rotation help the swing rather than arrive late?
6. Is follow-through complete and safe?

If an earlier layer fails, do not make a later layer the primary training target.
