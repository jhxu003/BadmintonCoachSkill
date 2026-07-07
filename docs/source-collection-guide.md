# Source Collection Guide

The source goal is complete indexing of public, accessible Liu Hui-related coaching material, followed by staged structure extraction.

## Source Priority

1. Official Liu Hui accounts and channels.
2. Authorized clip accounts.
3. Public videos and public live replays.
4. Public course catalogs and public training-camp announcements.
5. Public learner feedback and comment questions.
6. Third-party discussion, for auxiliary evidence only.

## Index First

Every discovered item must enter `data/source-index.tsv` before it is used in a rule.

Required fields:

```text
source_id, title, platform, url, published_at, access_type,
authorization_status, source_type, topic_tags, stroke_tags,
timestamps, usability, confidence, notes
```

## Extraction Rule

Extract original notes with source ids and timestamps. Do not copy long passages, full transcripts, screenshots, or private materials into public files.

