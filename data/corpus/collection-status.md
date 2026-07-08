# Liu Hui Corpus Collection Status

This is now a complete public-system skill build plus an expanded public Bilibili archive workflow, but it is not yet a completed all-platform all-video archive.

## Current Scope

- Official/public YouTube channel and video links discovered from public search.
- Authorized Bilibili clip/list pages discovered from public search and a public authorized live-teaching clip collection.
- Bilibili public list API fetch for `media_id=73830778`: 326 expected public items, 322 fetched public metadata items, 10 strict Liu Hui/Dagi candidates, 8 newly merged source rows, and 2 duplicate/existing rows.
- Bilibili public UGC season discovery from existing BVID seeds: 7 public seasons, 406 episode metadata rows, 383 newly merged source rows, and 23 exact BV-id duplicates recorded in `deduplication-map.yaml`.
- Douyin public search/profile discovery entries.
- Third-party discussion and channel-stat pages for auxiliary discovery.
- A full coaching taxonomy covering student profiles, power frameworks, stroke families, footwork families, correction order, drill families, training plans, and match transfer.
- A timestamp-review ledger covering all 21 previously blocked teaching points. The ledger records whole-clip title-backed notes and promotion decisions, but it does not claim internal timestamp completion where public subtitles or direct YouTube/Douyin access are unavailable.
- Deterministic examples for high clear, smash, rear-court footwork, front-court footwork, backhand, serve/receive, and doubles.

## Known Gap

The Liu Hui public video universe appears to be much larger than this source index. The repository therefore treats the current corpus as a complete public-system implementation with archive tracking, not as a completed video archive. Full-channel completion should be done by exporting public metadata with a compliant tool such as `yt-dlp --flat-playlist --dump-json`, Bilibili public APIs, or a platform-provided API, then converting that metadata into `data/source-index.tsv`.

Direct YouTube channel metadata fetch was attempted on 2026-07-08 and blocked by connection resets. Public search identified `@liuhuiyumaoqiu` with channel id `UCYFt9IXV8XwacWxhZFpPsTQ` and about 1.3K videos, but `yt-dlp` and RSS metadata export for that channel id are still blocked in this environment. The attempts are recorded in `public-access-log.tsv`.

Douyin direct profile metadata fetch was attempted on 2026-07-08 and did not produce stable per-video metadata. It remains a browser/API export task.

Bilibili archive state is recorded in `archive-manifest.yaml`. Raw fetched API pages remain under ignored `data/raw-private/`.

## Completion Rule

A source can enter deterministic coaching rules only after one of these is true:

- It has timestamped human notes.
- It is a short public clip whose title/description directly states the teaching point.
- Multiple independent public source titles support the same coarse teaching category, and the rule is marked `inferred`.

Raw transcripts and paid-course material stay out of git.
