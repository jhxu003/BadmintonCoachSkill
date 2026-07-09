# Corpus Provenance

This skill uses a public-safe corpus. It is not a complete archive of Liu Hui's teaching content.

## Source Tiers

- `official`: public Liu Hui channel/profile metadata.
- `authorized`: public pages or clip accounts that appear to have authorization.
- `public`: public videos, playlists, or search-discovered pages without authorization claims.
- `third_party`: discussion, stats, or learner commentary; auxiliary only.

## Evidence Status

- `ready_for_skill`: may support a rule or report if the output stays within the observable claim.
- `needs_timestamp_review`: may guide future annotation, but should not be phrased as a firm Liu Hui-derived rule.
- `whole_clip_title_backed`: a public video is indexed with a whole-clip time span because no public subtitle track was available; treat it as title-level evidence, not internal timestamp evidence.
- `content_model_candidate`: ASR/OCR/VLM/Pose has parsed at least part of the public video, but the output is still model-derived and pending human review; do not promote it to a firm skill rule.
- `timestamp_candidate_requires_human_review`: a model-derived timestamp window has been distilled into a usable hypothesis or guardrail, but it still requires human timestamp review before it can be described as source-backed.
- `title_level_reviewed_keep_inferred`: reviewed against the expanded public metadata corpus; may guide an inferred guardrail but must not be described as a timestamp-backed Liu Hui statement.
- `reviewed_not_promoted`: reviewed and intentionally kept out of firm rules because direct timestamp evidence is missing or platform access is blocked.

## Required Behavior

- Prefer source-backed or timestamped teaching points.
- Use candidate sources only to ask for review or to label a hypothesis.
- Apply `references/reviewed-corpus-rules.yaml` before using any teaching point that still has `needs_timestamp_review` in the corpus file.
- Never quote or reconstruct course text.
- Never claim Liu Hui endorsed this skill or personally reviewed the user's video.
- When a source is third-party, use it only for product/user insight, not technical authority.

## Current Corpus Files

- `data/source-index.tsv`
- `data/corpus/teaching-points.yaml`
- `data/corpus/timestamp-review.yaml`
- `data/corpus/video-pilot-manifest.yaml`
- `data/corpus/video-evidence-index.tsv`
- `data/corpus/video-asr-teaching-windows.yaml`
- `data/corpus/deduplication-map.yaml`
- `data/corpus/collection-status.md`
