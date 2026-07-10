# Liu Hui-Inspired Coaching System

This file stores original, research-oriented summaries derived from public source indexing. It is not an official Liu Hui document.

## Corpus Status

The current runtime system is complete against the accessible non-YouTube public Bilibili index in this repository, not an official Liu Hui archive. YouTube is excluded by project decision. Douyin and Instagram remain explicit access gaps because stable public per-video metadata or media access is unavailable.

The Bilibili corpus contains 409 independent video jobs after removing 2 discovery-only rows. Of these, 408 are accessible and have reviewed full-audio `mobiuslabsgmbh/faster-whisper-large-v3-turbo` coverage; one public page resolves to a missing-video placeholder. The reviewed layer contains 2610 public-safe timestamp windows across all 408 accessible sources.

The visual layer contains 402 action or visible-demonstration sources and 6064 teaching-window keyframes, with 6 conceptual or equipment sources explicitly marked ASR-only. Qwen3-VL-8B-Instruct v4 provides schema-validated still-frame visibility candidates, and sparse Pose provides body-keypoint visibility. A critical temporal layer adds 408 dense sequences and 5304 frames across 204 sources. Public summaries expose only timestamps, visibility aggregates, coarse 2D proxies, evidence levels, and confidence boundaries; private images, model text, and coordinates remain outside git.

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

## Video Corpus Distillation

`data/corpus/video-asr-teaching-windows-full.yaml` stores the full candidate-window layer. `data/corpus/video-asr-timestamp-review.yaml` stores the complete public-safe agent review. `data/corpus/video-visual-pipeline-manifest.yaml` defines sparse visual coverage, `data/corpus/video-temporal-review-manifest.yaml` defines the critical dense sequences, and `references/multimodal-evidence-map.yaml` bundles the source-to-framework explainability chain for standalone skill use. Raw ASR text, audio, video, OCR, VLM outputs, keypoint coordinates, cookies, tokens, temporary media URLs, and paid-course material must stay private.

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
