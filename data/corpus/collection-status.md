# Liu Hui Corpus Collection Status

This is a complete accessible non-YouTube public Bilibili system build, not a completed all-platform archive and not an official Liu Hui corpus.

## Current Scope

- YouTube discovery rows are retained for provenance but excluded from completion accounting by project decision.
- Authorized Bilibili clip/list pages discovered from public search and a public authorized live-teaching clip collection.
- Bilibili public list API fetch for `media_id=73830778`: 326 expected public items, 322 fetched public metadata items, 10 strict Liu Hui/Dagi candidates, 8 newly merged source rows, and 2 duplicate/existing rows.
- Bilibili public UGC season discovery from existing BVID seeds: 7 public seasons, 406 episode metadata rows, 383 newly merged source rows, and 23 exact BV-id duplicates recorded in `deduplication-map.yaml`.
- Douyin public search/profile discovery entries.
- Third-party discussion and channel-stat pages for auxiliary discovery.
- A full coaching taxonomy covering student profiles, power frameworks, stroke families, footwork families, correction order, drill families, training plans, and match transfer.
- A timestamp-review ledger covering all 21 previously blocked teaching points. The ledger records whole-clip title-backed notes and promotion decisions, but it does not claim internal timestamp completion where public subtitles or direct YouTube/Douyin access are unavailable.
- A content-level model pilot over 30 indexed public Bilibili videos, with 30 successful VLM jobs, 25 successful ASR jobs, 90 public-safe timestamp candidate teaching windows, and candidate-window distillation into skill rules, rubrics, drills, and training plans.
- A full-audio ASR pass over the remaining indexed public Bilibili corpus: 378 of 379 jobs succeeded; 1 public page is currently unavailable. Combined scanning produced 2567 timestamp candidates across 401 sources.
- A complete public-safe ASR timestamp review over all 2567 windows, with 2491 direct ASR topic matches, 76 title-supported intervals, 401 reviewed sources, zero missing manifest jobs, and zero missing ASR artifacts behind the reviewed windows.
- A visual completion manifest covering 396 action-bearing sources with 5977 planned teaching-window keyframes; 5 conceptual sources are explicitly ASR-only.
- Existing private VLM parsing for 30 pilot sources and 336 keyframes, reduced to public-safe timestamp and visibility counts.
- A representative GPU pose pilot covering 6 action sources and 107 teaching-window keyframes; body keypoints were detected in all 107 frames and reduced to public-safe aggregate coverage without coordinates.
- Instagram and Douyin retries on 2026-07-10 remained blocked; they stay discovery-level and are not counted as parsed evidence.
- Deterministic examples for high clear, smash, rear-court footwork, front-court footwork, backhand, serve/receive, and doubles.

## Known Gap

The repository treats the current corpus as complete against its accessible non-YouTube Bilibili index, not as proof that every Liu Hui video ever published is present. New Bilibili public seasons or lists should be imported and passed through the same ASR timestamp review and visual queue before they are counted as covered.

YouTube is intentionally excluded from this completion target. Historical discovery and access attempts remain in `public-access-log.tsv` for provenance only.

Douyin was retried on 2026-07-10 and still returned a dynamic 404 without stable per-video metadata. Instagram direct HTTP and `yt-dlp` access also timed out. These are explicit access gaps, not parsed sources.

Bilibili archive state is recorded in `archive-manifest.yaml`. Raw fetched API pages remain under ignored `data/raw-private/`.

## Completion Rule

A source can enter deterministic coaching rules only after one of these is true:

- It has timestamped human notes.
- It is a short public clip whose title/description directly states the teaching point.
- Multiple independent public source titles support the same coarse teaching category, and the rule is marked `inferred`.

An `asr_timestamp_reviewed_public_safe` interval may enter framework routing and guardrail logic, but visible mechanics still require direct frame evidence before a firm biomechanical claim.

Raw transcripts and paid-course material stay out of git.

## Content-Level Parsing Pilot

On 2026-07-08 and 2026-07-09, a content-level ASR/VLM pilot was run for 30 indexed public Bilibili jobs.

- `faster-whisper tiny` completed in the first pilot but was rejected for skill distillation because badminton-specific terms were unstable.
- `mobiuslabsgmbh/faster-whisper-large-v3-turbo` on the first 180 seconds is the accepted ASR model for candidate-window extraction.
- 30 of 30 jobs produced `content_model_candidate` evidence.
- 30 of 30 jobs have private VLM parsing output and public-safe evidence records.
- 25 of 30 jobs produced ASR windows from the first 180 seconds of audio.
- 5 of 30 jobs are currently VLM-only and should not be used for speech-derived teaching-window claims until audio/ASR is added.
- 90 pilot timestamp candidates remain in the historical pilot file; the full-corpus review file supersedes them for any window with full ASR coverage.
- The current skill distills these windows into candidate-level rules, rubrics, drills, and training plans with `timestamp_candidate_requires_human_review` or `timestamp_candidate` status.
- Raw ASR segments remain private under `data/raw-private/video-corpus/`.
- Compute-node runs from shared `/dataStor` Python environments hit NFS wait states; full batch parsing should use a conda-packed runtime, model cache, and audio/video intermediates on node-local storage before scaling.

## Full Bilibili ASR Pass

On 2026-07-09, the expanded Bilibili corpus was processed with full-audio ASR.

- Manifest: `video-corpus-manifest.yaml`
- Jobs: 379
- ASR ok: 378
- Unavailable: `LH_BILI_CORE_COMPETITION`
- Public evidence files indexed: 409
- Full candidate-window file: `video-asr-teaching-windows-full.yaml`
- Candidate windows: 2567
- Sources with candidate windows: 401

All 2567 full-corpus windows are now represented in `video-asr-timestamp-review.yaml` as `agent_asr_timestamp_reviewed` and `asr_timestamp_reviewed_public_safe`. They support framework routing, timestamp lookup, diagnostic questions, and review queues, but not exact quotation, human-review claims, or visual biomechanical conclusions.

## Visual Review Coverage

On 2026-07-10, the reviewed ASR windows were converted into a complete visual-review queue.

- Sources with reviewed ASR windows: 401
- Action-bearing visual jobs: 396
- Conceptual ASR-only sources: 5
- Planned keyframes: 5977
- Existing private VLM sources: 30
- Existing VLM keyframes summarized: 336
- Representative pose sources: 6
- Pose keyframes summarized: 107
- Pose keyframes with detected people: 107

The queue prioritizes the lower-density categories `doubles`, `drive`, `serve_receive`, `drop`, and `footwork`, plus biomechanical claims involving contact point, top elbow, hip/trunk timing, wrist/grip, racket preparation, and internal-rotation proxies.

The pose pilot spans footwork, drop, receive-smash defense, push/drive, doubles rear-court continuity, and top-elbow teaching. Its aggregates show whether body landmarks are visible at a timestamp; they do not prove racket orientation, contact point, true shoulder internal rotation, or coaching intent.
