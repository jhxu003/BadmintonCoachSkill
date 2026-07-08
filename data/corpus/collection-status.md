# Liu Hui Corpus Collection Status

This is now a complete public-system skill build within current access constraints, but it is not a completed all-video archive.

## Current Scope

- Official/public YouTube channel and video links discovered from public search.
- Authorized Bilibili clip/list pages discovered from public search and a public authorized live-teaching clip collection.
- Douyin public search/profile discovery entries.
- Third-party discussion and channel-stat pages for auxiliary discovery.
- A full coaching taxonomy covering student profiles, power frameworks, stroke families, footwork families, correction order, drill families, training plans, and match transfer.
- Deterministic examples for high clear, smash, rear-court footwork, front-court footwork, backhand, serve/receive, and doubles.

## Known Gap

The Liu Hui public video universe appears to be much larger than this source index. The repository therefore treats the current corpus as a complete public-system implementation, not as a complete video archive. Full-channel completion should be done by exporting public metadata with a compliant tool such as `yt-dlp --flat-playlist --dump-json` or a platform-provided API, then converting that metadata into `data/source-index.tsv`.

Direct YouTube channel metadata fetch was attempted on 2026-07-08 and blocked by connection resets. The failed attempts are recorded in `public-access-log.tsv`.

## Completion Rule

A source can enter deterministic coaching rules only after one of these is true:

- It has timestamped human notes.
- It is a short public clip whose title/description directly states the teaching point.
- Multiple independent public source titles support the same coarse teaching category, and the rule is marked `inferred`.

Raw transcripts and paid-course material stay out of git.
