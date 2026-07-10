# Corpus Provenance

This skill uses a public-safe corpus. It is complete against the accessible non-YouTube Bilibili index in this repository, not a claim of owning every Liu Hui video across every platform.

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
- `full_corpus_timestamp_candidate_requires_human_review`: the expanded full-audio ASR corpus supports a broad candidate pattern across many public videos, but the pattern is still model-derived and must not be described as exact Liu Hui wording or human-reviewed timestamp evidence.
- `asr_timestamp_reviewed_public_safe`: the private ASR interval was checked by the build agent and reduced to an original topic summary, timestamp, counts, and evidence limits. It may support framework routing and diagnostic questions, but is not a quote, human review, or visual proof.
- `visual_model_candidate_reviewed_public_safe`: private VLM keyframes were reduced to public-safe visibility counts and timestamp pointers. It may identify frames for review, but cannot independently prove contact, racket-face geometry, elbow sequence, hip timing, or internal rotation.
- `pose_model_candidate_reviewed_public_safe`: private pose output was reduced to detection coverage and confidence without coordinates. It may show whether body keypoints are visible, but cannot see racket orientation or prove badminton biomechanics.
- `title_level_reviewed_keep_inferred`: reviewed against the expanded public metadata corpus; may guide an inferred guardrail but must not be described as a timestamp-backed Liu Hui statement.
- `reviewed_not_promoted`: reviewed and intentionally kept out of firm rules because direct timestamp evidence is missing or platform access is blocked.

## Required Behavior

- Prefer source-backed or reviewed timestamp teaching points.
- Use `asr_timestamp_reviewed_public_safe` for topic routing and pair biomechanical claims with direct user-video observations or reviewed visual frames.
- Use VLM and pose summaries to locate visible timestamps, not to substitute for frame review.
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
- `data/corpus/video-asr-teaching-windows-full.yaml`
- `data/corpus/video-asr-timestamp-review.yaml`
- `data/corpus/video-visual-review-manifest.yaml`
- `data/corpus/video-visual-evidence-summary.yaml`
- `data/corpus/video-pose-evidence-summary.yaml`
- `data/corpus/video-parse-status.md`
- `data/corpus/deduplication-map.yaml`
- `data/corpus/collection-status.md`
