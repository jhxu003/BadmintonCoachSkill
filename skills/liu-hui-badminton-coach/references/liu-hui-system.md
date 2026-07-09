# Liu Hui-Inspired Coaching System

This file stores original, research-oriented summaries derived from public source indexing. It is not an official Liu Hui document.

## Corpus Status

The current runtime system is complete against the public-source index in this repository, not an official Liu Hui archive. Use `data/source-index.tsv` and `data/corpus/teaching-points.yaml` for provenance. Do not promote `needs_timestamp_review` points into firm rules without timestamped review.

The video-content pilot has processed 30 indexed public Bilibili teaching videos. Private VLM parsing succeeded for all 30 videos. ASR succeeded for 25 videos, producing 90 timestamp candidate teaching windows; 5 sources are currently VLM-only and require audio/ASR before speech-derived teaching-window claims. These windows have been distilled into `timestamp_candidate_requires_human_review` rules, timestamp-candidate frameworks, rubrics, drills, and training plans, but they remain model-derived until human timestamp review.

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

`data/corpus/video-asr-teaching-windows.yaml` stores public-safe original summaries only. Raw ASR text, audio, video, OCR, VLM outputs, cookies, tokens, and paid-course material must stay private.

Use timestamp-candidate material as follows:

- It may guide a hypothesis, observation request, drill choice, or human-review queue.
- It may be cited by `evidence_ids` for internal traceability.
- It must not be described as Liu Hui's exact words or as human-reviewed timestamp evidence.
- It must not override earlier observable layers such as arrival, contact point, frame, elbow sequence, and safety.
## Priority Heuristic

1. Can the player arrive in time and stay balanced?
2. Is contact in a playable front-high window?
3. Is the racket-side frame stable enough to transfer force?
4. Does elbow lead before wrist acceleration?
5. Does hip/trunk rotation help the swing rather than arrive late?
6. Is follow-through complete and safe?

If an earlier layer fails, do not make a later layer the primary training target.
