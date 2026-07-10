# Corpus Build

This directory stores public-safe corpus artifacts for the Liu Hui badminton coach skill.

It must contain only:

- Public source indexes and discovery notes.
- Original, short teaching-point summaries.
- Source ids and timestamp pointers.
- Review status and provenance labels.

It must not contain raw videos, full subtitles, paid-course transcripts, screenshots, cookies, exported account data, or long copied passages.

## Layers

1. `data/source-index.tsv`: canonical list of discovered public sources.
2. `teaching-points.yaml`: distilled coaching points tied to source ids.
3. `timestamp-review.yaml`: review ledger for timestamp-blocked or title-level reviewed points.
4. `deduplication-map.yaml`: exact duplicate and deferred duplicate decisions.
5. Skill references: use `ready_for_skill` points directly; use reviewed title-level points only through skill guardrails; keep `reviewed_not_promoted` points out of deterministic Liu Hui-derived rules.
6. `video-asr-teaching-windows-full.yaml`: expanded public-safe ASR candidate windows from the full indexed Bilibili corpus.
7. `video-asr-timestamp-review.yaml`: public-safe agent review for every full-corpus ASR window; no transcript text is included.
8. `video-visual-review-manifest.yaml`: complete visual-review queue for action-bearing Bilibili sources.
9. `video-visual-evidence-summary.yaml`: safe timestamp and visibility summary from private VLM output.
10. `video-parse-status.md`: coverage report for video parsing runs and known unavailable sources.

## Evidence Labels

- `source_title`: supported by public title and page metadata.
- `timestamp_note`: supported by timestamped human notes.
- `whole_clip_title_backed`: whole public clip span is recorded, but no internal timestamp/subtitle evidence is available.
- `inferred_from_titles`: plausible synthesis from multiple titles, not enough for direct quotation.
- `asr_timestamp_reviewed_public_safe`: private ASR interval checked and reduced to an original topic/timestamp summary; not human review or visual proof.
- `visual_model_candidate_reviewed_public_safe`: VLM visibility summary for locating frames; not standalone biomechanical proof.
- `pose_model_candidate_reviewed_public_safe`: aggregate body-keypoint coverage; no coordinates and no racket/rotation proof.
- `third_party`: discussion or learner feedback; auxiliary only.
