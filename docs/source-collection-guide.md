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

## Corpus Build Commands

Print the current public corpus coverage:

```bash
python3 scripts/build_corpus_report.py
```

Convert public YouTube channel metadata exported by `yt-dlp`:

```bash
yt-dlp --flat-playlist --dump-json "https://www.youtube.com/@liuhuiyumaoqiu/videos" > data/raw-private/yt-official.jsonl
yt-dlp --flat-playlist --dump-json "https://www.youtube.com/channel/UCYFt9IXV8XwacWxhZFpPsTQ/videos" > data/raw-private/yt-official-canonical-id.jsonl
python3 scripts/import_yt_dlp_jsonl.py data/raw-private/yt-official.jsonl --source-prefix LH_YT_AUTO --authorization-status official > data/raw-private/yt-official.tsv
```

Review the TSV manually before merging rows into `data/source-index.tsv`.

If direct channel metadata fetch fails, add a row to `data/corpus/public-access-log.tsv` with the exact command or URL, date, error result, and next action.

Convert public Bilibili UGC season metadata exported from `x/web-interface/view`:

```bash
python3 scripts/import_bilibili_view_season.py data/raw-private/bili-discovered-seasons/*.json --source-prefix LH_BILI_SEASON > data/raw-private/bili-seasons-all.tsv
```

Merge only new BV ids into `data/source-index.tsv`; record exact duplicate BV ids in `data/corpus/deduplication-map.yaml`.

## Source Status

- `usable`: public metadata is sufficient for source indexing or title-level teaching-point support.
- `candidate`: discovered but still needs direct page verification or timestamp review.
- `auxiliary`: useful for discovery, market/user insight, or corpus scale, but not direct coaching evidence.

## Rule Promotion

A teaching point can support deterministic rules only when:

- It is marked `ready_for_skill` in `data/corpus/teaching-points.yaml`.
- Its `source_ids` exist in `data/source-index.tsv`.
- Its evidence is not only third-party discussion.
- The rule still states whether its confidence is `source_backed`, `inferred`, or `hypothesis`.
