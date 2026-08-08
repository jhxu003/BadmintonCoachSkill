# Video Evidence Web App

## What It Does

The web application exposes two independent flows. The default coach-demonstration flow requires no learner video:

1. Select a coach system, action, learning level, and action phase.
2. Select an action-compatible teaching framework.
3. Locate same-phase public coach-video references declared by the framework sources.
4. Download only the selected source on a worker, extract a keyframe and short clip, then remove the transient full video.
5. Return the teaching route, source timestamp, media, visible facts, and evidence boundaries under a 24-hour access token.

The learner-video Agent turns one uploaded badminton video into a bounded, evidence-linked coaching report. It can separate up to five non-overlapping action candidates in one upload:

1. Normalize the video to a stable H.264 analysis derivative.
2. Use local Qwen2.5-VL 3B to propose only sustained, non-overlapping athletic action windows, then release that model.
3. For each high-confidence window, track one visible player with YOLO pose and require a complete seven-stage package: preparation, start, arrival, top elbow, action window, follow-through, and recovery.
4. Use local Qwen2.5-VL 7B to fill only the rule-backed, visually safe observation vocabulary, then release that model.
5. Run the compatible three-coach Skill only when the route, seven-stage package, observation confidence, and deterministic teaching focus all pass.
6. Materialize only exact-topic, reviewed coach lessons selected by that Skill and provide a timestamp link back to the original platform.

The Agent is fail-closed. A low-confidence route, incomplete action package, malformed visual-model result, unsupported action, or missing deterministic teaching focus returns a retake/setup instruction instead of a diagnosis. Raw model output is never stored in the browser report.

The report deliberately treats contact timing, internal rotation, force, grip pressure, racket-face angle, and calibrated three-dimensional mechanics as unavailable from ordinary single-camera video.

## Runtime Requirements

- Python 3.10 or later.
- Node.js 20 or later.
- NVIDIA GPU with CUDA for learner-video analysis. Coach-demonstration requests do not load YOLO or Qwen-VL.
- FFmpeg, supplied by the Conda environment or `imageio-ffmpeg`.
- Local Qwen-VL checkpoints available to the GPU worker. The shipped Agent configuration uses `Qwen/Qwen2.5-VL-3B-Instruct` for routing and `Qwen/Qwen2.5-VL-7B-Instruct` for bounded observation.

Create the environment and install application dependencies:

```bash
conda env create -f environment-video.yml
conda activate badminton-video
python -m pip install -e .
npm --prefix web ci
```

## Run Locally On A GPU Host

```bash
export BADMINTON_PROJECT_ROOT="$PWD"
export BADMINTON_RUNTIME_ROOT="$HOME/.cache/badminton-coach-runtime"
export BADMINTON_POSE_MODEL_PATH="$MODEL_ROOT/yolo11n-pose.pt"
export BADMINTON_VLM_MODEL_PATH="$MODEL_ROOT/qwen-vl"
export BADMINTON_AGENT_ROUTER_MODEL_PATH="$MODEL_ROOT/qwen2.5-vl-3b"
export BADMINTON_AGENT_OBSERVER_MODEL_PATH="$MODEL_ROOT/qwen2.5-vl-7b"
uvicorn badminton_coach_skill.web.app:create_app --factory --host 0.0.0.0 --port 8000
```

The optional `BADMINTON_POSE_MODEL_PATH`, `BADMINTON_VLM_MODEL_PATH`, `BADMINTON_AGENT_ROUTER_MODEL_PATH`, and `BADMINTON_AGENT_OBSERVER_MODEL_PATH` settings override model identifiers in `configs/video-analysis.yaml`. Point them to pre-downloaded model files or directories on an offline server or shared GPU cluster so the worker does not fetch weights while processing an upload. The 3B router, YOLO stage, and 7B observer are intentionally sequential; bounded image sampling and explicit cache release let them share one GPU.

Start the browser client in another terminal:

```bash
npm --prefix web run dev -- --host 0.0.0.0
```

## Dispatch Modes

`BADMINTON_DISPATCH_MODE=local` is the default. It processes one task at a time in the API host. The host needs GPU access only when learner-video analysis is enabled.

For a separate GPU worker, set the following before starting the API and worker:

```bash
export BADMINTON_DISPATCH_MODE=celery
export CELERY_BROKER_URL=redis://localhost:6379/0
celery -A badminton_coach_skill.web.worker.celery_app worker --loglevel=INFO
celery -A badminton_coach_skill.web.worker.celery_app beat --loglevel=INFO
```

The worker uses the same environment variables as the API. The periodic Celery task removes expired student media every hour.

On HPC nodes where the Conda environment lives on a high-latency shared filesystem, set `BADMINTON_YTDLP_MODE=in_process`. This reuses the running worker process instead of starting a second Python interpreter for each public coach source. The default `subprocess` mode remains suitable for local filesystems.

## HTTP Interface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/demonstrations` | Create a coach teaching demonstration without learner video. |
| `POST` | `/api/analyses` | Upload a video and create an analysis job. |
| `GET` | `/api/analyses/{analysis_id}` | Read state and progress. |
| `GET` | `/api/analyses/{analysis_id}/report` | Read the completed public-safe report. |
| `GET` | `/api/analyses/{analysis_id}/frames/{asset_id}` | Read a selected student keyframe only. |
| `GET` | `/api/coach-references/{reference_id}/frame` | Read a cached coach reference frame. |
| `GET` | `/api/coach-references/{reference_id}/clip` | Read a cached coach reference clip. |
| `DELETE` | `/api/analyses/{analysis_id}` | Delete all private student media immediately. |
| `WS` | `/api/analyses/{analysis_id}/events` | Receive progress updates. |

Student upload requests stream to disk in chunks rather than loading the entire video into API memory.
Both creation endpoints return a random access token exactly once. Send it as `X-Analysis-Token` for job status, reports, deletion, and frame requests; browser image and WebSocket requests use the `access_token` query parameter because those browser APIs cannot attach a custom header. Keep the token only in the active browser session—reloading the page intentionally does not restore a private task.

To opt into the Agent upload contract, submit `analysis_mode=agent_video_coaching` with `coach_id=auto`; omit `action_hint`. Existing uploads without `analysis_mode` keep the legacy explicit `coach_id` and `action_hint` behavior.

## Privacy And Media Lifetime

- Original uploads, normalized derivatives, selected student frames, and model intermediates are private deployment media.
- Each analysis has a 24-hour expiry by default; set `ANALYSIS_TTL_HOURS` only when a deployment needs a longer retention period.
- Deleting an analysis immediately removes its private media and marks the job expired.
- The application never exposes the original upload through a frame endpoint.
- Coach reference media is downloaded only for a selected demonstration or matched diagnostic report, extracted to a cached image and short clip, and the temporary full source download is removed.
- Git must not contain uploads, private runtime frames, model outputs, caches, database files, logs, or access tokens. The only exceptions are the 16 owner-approved, source-attributed coach Pages demonstration asset sets documented in [`github-pages-demo.md`](github-pages-demo.md); they contain no learner media or runtime cache.

## When A Video Is Not Usable

The Agent may reject all candidates when the video contains an explanation shot, static gesture, severe crop, overlapping action windows, or insufficient action evidence. In that case the report completes without a fabricated diagnosis and returns retake guidance: use a side or rear-side view, keep the full body and racket side visible, and record continuously from movement start through recovery. Multi-player and tactical segments require the dedicated role/court workflow; the Agent does not infer identities, intent, or the next shot.
