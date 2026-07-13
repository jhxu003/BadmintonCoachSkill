# Video Agent Contract

The video agent must output data compatible with `player-profile.schema.json` and `video-observation.schema.json`.

## Responsibilities

- Identify the action: high clear, smash, drop, drive, rear/front footwork, backhand, serve/receive, doubles, or match transfer.
- Provide keyframes with timestamps.
- Provide observable proxies for contact, elbow, wrist/elbow sequence, hip/shoulder sequence, frame, finish, footwork, landing, recovery, and rally context when applicable.
- Explicitly list missing observations.

## Non-Responsibilities

The coaching runtime consumes structured observations. A video-analysis agent or a human reviewer produces those observations.

If the video agent cannot see a feature, it must mark that feature as missing.
