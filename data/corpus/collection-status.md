# Liu Hui Corpus Collection Status

This is not yet a completed all-video corpus. It is the first reproducible public-source build.

## Current Scope

- Official/public YouTube channel and video links discovered from public search.
- Authorized Bilibili clip/list pages discovered from public search.
- Douyin public search/profile discovery entries.
- Third-party discussion and channel-stat pages for auxiliary discovery.

## Known Gap

The Liu Hui public video universe appears to be much larger than this seed index. The repository therefore treats the current corpus as a traceable seed, not as a complete archive. Full-channel completion should be done by exporting public metadata with a compliant tool such as `yt-dlp --flat-playlist --dump-json` or a platform-provided API, then converting that metadata into `data/source-index.tsv`.

## Completion Rule

A source can enter deterministic coaching rules only after one of these is true:

- It has timestamped human notes.
- It is a short public clip whose title/description directly states the teaching point.
- Multiple independent public source titles support the same coarse teaching category, and the rule is marked `inferred`.

Raw transcripts and paid-course material stay out of git.
