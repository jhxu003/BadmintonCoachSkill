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
3. Skill references: only use points marked `ready_for_skill`; keep `needs_timestamp_review` points out of deterministic rules until reviewed.

## Evidence Labels

- `source_title`: supported by public title and page metadata.
- `timestamp_note`: supported by timestamped human notes.
- `inferred_from_titles`: plausible synthesis from multiple titles, not enough for direct quotation.
- `third_party`: discussion or learner feedback; auxiliary only.
