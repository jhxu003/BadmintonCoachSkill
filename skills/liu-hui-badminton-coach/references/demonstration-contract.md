# Teaching Demonstration Contract

Use this mode to explain and show a coach-side action without learner video.

1. Require an action and desired phase; use level, training goal, or framework id only to narrow the teaching route.
2. Select an action-compatible framework before selecting media.
3. Prefer `agent_reviewed` entries in `reviewed-demonstrations.yaml`, then prefer source ids declared by the selected framework and require the reference action and phase to match.
4. Return the original source id, title, timestamp, jump link, visible facts, limitations, and frame or clip availability.
5. State whether the timepoint is `agent_reviewed`, `model_candidate`, or `timestamp_only`. Describe it as a public coach-video demonstration reference, not official certification or independent proof of every mechanic.
6. Use a still for posture navigation and a clip for process context. Do not turn either into claims about exact contact, racket-face angle, force, grip pressure, true rotation, or calibrated 3D motion.
7. Return `no_reliable_same_phase_demonstration_frame` when the indexed evidence is insufficient. Never substitute another phase.
