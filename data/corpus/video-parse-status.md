# Video Parse Status

Updated: 2026-07-09

This file is public-safe. It records coverage counts and failure classes only. Raw video, audio, ASR text, metadata dumps, model logs, cookies, and temporary media URLs stay under ignored `data/raw-private/`.

## Bilibili Public Corpus

- Full remaining Bilibili corpus manifest: `video-corpus-manifest.yaml`
- Jobs in manifest: 379
- Full-audio ASR completed: 378
- Unavailable public page: 1
- Public evidence files indexed: 409
- ASR model: `mobiuslabsgmbh/faster-whisper-large-v3-turbo`
- Audio scope: full audio

Unavailable source:

- `LH_BILI_CORE_COMPETITION` / `corpus-370-lh_bili_core_competition`: public page currently resolves to a missing-video placeholder (`视频去哪了呢？`) and `yt-dlp` cannot extract audio.

## Full Teaching-Window Candidates

- Manifests scanned: `video-pilot-manifest.yaml`, `video-corpus-manifest.yaml`
- Jobs scanned: 409
- Sources with teaching-window candidates: 401
- Public-safe candidate windows: 2567
- Output: `video-asr-teaching-windows-full.yaml`

Top candidate topic counts:

| Topic | Windows |
|---|---:|
| diagnosis_flow | 1411 |
| training_plan | 1212 |
| smash | 1158 |
| student_fit | 1026 |
| top_elbow | 1024 |
| internal_rotation | 814 |
| racket_preparation | 689 |
| high_clear | 651 |
| wrist | 589 |
| safety | 563 |
| hip_rotation | 413 |
| contact_point | 410 |
| match_transfer | 271 |
| footwork | 263 |
| drop | 257 |
| serve_receive | 132 |
| drive | 128 |
| doubles | 66 |

## Interpretation

The expanded corpus supports a broad Liu Hui-style runtime system centered on student-fit diagnosis, training-plan selection, overhead/smash power-chain analysis, frame and release mechanics, transfer to match pressure, and staged drills.

All full-corpus windows remain `pending_human_review`. They can guide framework selection and review queues, but they must not be described as exact Liu Hui wording or human-reviewed timestamp evidence.

## Extra Platform Sources

- Extra platform manifest: `video-extra-platform-manifest.yaml`
- Jobs: 25
- Platforms: YouTube, Instagram
- Audio/ASR result in this environment: 0 ok, 25 skipped
- Retry manifest: `video-extra-platform-asr-retry-manifest.yaml`

The YouTube sources were discovered and indexed, but direct `yt-dlp` access from this environment failed with network reachability / address-family errors. These sources remain discovery and title-level context until platform access is available.
