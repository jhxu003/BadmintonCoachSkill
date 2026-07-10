# Video Parse Status

Updated: 2026-07-10

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

## ASR Timestamp Review

- Manifests scanned: `video-pilot-manifest.yaml`, `video-corpus-manifest.yaml`
- Jobs scanned: 409
- Sources with teaching-window candidates: 401
- Public-safe candidate windows: 2567
- Agent-reviewed ASR timestamp windows: 2567
- ASR topic signal confirmed inside the timestamp: 2491
- Timestamp has ASR but topic still depends on the public title: 76
- Missing manifest jobs behind reviewed windows: 0
- Missing or failed ASR artifacts behind reviewed windows: 0
- Candidate output: `video-asr-teaching-windows-full.yaml`
- Reviewed output: `video-asr-timestamp-review.yaml`

Top candidate topic counts:

| Topic | Windows |
|---|---:|
| diagnosis_flow | 1429 |
| training_plan | 1237 |
| smash | 1163 |
| student_fit | 1041 |
| top_elbow | 1035 |
| internal_rotation | 834 |
| racket_preparation | 691 |
| high_clear | 656 |
| safety | 619 |
| wrist | 599 |
| hip_rotation | 424 |
| contact_point | 422 |
| match_transfer | 284 |
| footwork | 269 |
| drop | 262 |
| serve_receive | 135 |
| drive | 134 |
| doubles | 70 |

## Visual Completion Layer

- Sources with reviewed ASR windows: 401
- Action-bearing visual review jobs: 396
- Conceptual ASR-only sources: 5
- Planned teaching-window keyframes: 5977
- Existing private VLM sources: 30
- Existing VLM keyframes summarized: 336
- VLM visibility descriptions: 269 player-position, 269 racket-preparation, 25 contact/pre-contact, 255 lower-body, and 21 recovery observations
- Representative GPU pose sources: 6
- Pose keyframes summarized: 107
- Pose keyframes with detected people: 107
- Pose model: `yolo11n-pose.pt`
- Visual queue: `video-visual-review-manifest.yaml`
- Public-safe VLM summary: `video-visual-evidence-summary.yaml`
- Public-safe pose summary: `video-pose-evidence-summary.yaml`

The visual queue covers overhead mechanics, footwork, drop, drive, serve/receive, doubles, contact point, top elbow, hip/trunk timing, wrist/grip, and internal-rotation proxy review. VLM output is used to locate frames with visible evidence; it is not standalone proof of a biomechanical claim.

The pose pilot sampled footwork, drop, receive-smash defense, push/drive, doubles continuity, and top-elbow sources. Pose output is used only to confirm body-keypoint visibility and prioritize later frame review; aggregate detections cannot establish racket-face geometry, contact, true joint rotation, or Liu Hui's intent.

## Interpretation

The expanded corpus supports a broad Liu Hui-style runtime system centered on student-fit diagnosis, training-plan selection, overhead/smash power-chain analysis, frame and release mechanics, transfer to match pressure, and staged drills.

All 2567 full-corpus windows now have `agent_asr_timestamp_reviewed` public-safe summaries. They can guide framework selection, timestamp lookup, diagnostic questions, and review queues. They must not be described as exact Liu Hui wording, human-reviewed evidence, or visual proof of contact point, top elbow, hip timing, racket face, or internal rotation.

## Non-YouTube Platform Boundary

- YouTube: excluded by project decision and not part of completion accounting.
- Instagram: the indexed public reel timed out through both direct HTTP and `yt-dlp` on 2026-07-10.
- Douyin: the public profile still returns a dynamic HTTP 404 and no stable per-video metadata export.

Instagram and Douyin remain discovery-level access gaps. They are not counted as parsed video evidence and cannot support deterministic technical rules until stable public metadata and media access are available.
