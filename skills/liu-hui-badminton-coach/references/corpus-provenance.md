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

## Required Behavior

- Prefer source-backed or timestamped teaching points.
- Use candidate sources only to ask for review or to label a hypothesis.
- Never quote or reconstruct course text.
- Never claim Liu Hui endorsed this skill or personally reviewed the user's video.
- When a source is third-party, use it only for product/user insight, not technical authority.

## Current Corpus Files

- `data/source-index.tsv`
- `data/corpus/teaching-points.yaml`
- `data/corpus/collection-status.md`
