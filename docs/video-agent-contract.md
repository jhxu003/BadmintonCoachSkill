# Video Agent Contract

The video agent must output `player-profile.schema.json` and `video-observation.schema.json` compatible data.

## Responsibilities

- Identify the action: high clear, smash, or rear-court footwork.
- Provide keyframes with timestamps.
- Provide observable proxies for contact, elbow, wrist/elbow sequence, hip/shoulder sequence, frame, finish, and footwork.
- Explicitly list missing observations.

## Non-Responsibilities

The Liu Hui skill does not read raw video. It consumes structured facts.

If the video agent cannot see a feature, it must mark that feature as missing.

