# Video Evidence Web App

## What It Does

The web application turns one uploaded badminton action video into a bounded, evidence-linked coaching report:

1. Normalize the video to a stable H.264 analysis derivative.
2. Track one visible player with YOLO pose.
3. Select candidate preparation, start, arrival, top-elbow, contact-window proxy, follow-through, and recovery frames.
4. Use Qwen-VL to reject static talking, gesturing, and instruction shots that are not credible action-phase evidence.
5. Run the selected coach Skill against only the retained visual evidence.
6. Materialize only matched public coach reference frames and provide a timestamp link back to the original platform.

The report deliberately treats contact timing, internal rotation, force, grip pressure, racket-face angle, and calibrated three-dimensional mechanics as unavailable from ordinary single-camera video.

## Runtime Requirements

- Python 3.10 or later.
- Node.js 20 or later.
- NVIDIA GPU with CUDA for real video analysis.
- FFmpeg, supplied by the Conda environment or `imageio-ffmpeg`.
- A local or remotely resolvable Qwen-VL model. The shipped configuration uses `Qwen/Qwen2.5-VL-3B-Instruct`.

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
export BADMINTON_VLM_MODEL_PATH="/models/qwen-vl"
uvicorn badminton_coach_skill.web.app:create_app --factory --host 0.0.0.0 --port 8000
```

The optional `BADMINTON_VLM_MODEL_PATH` setting overrides the model identifier in `configs/video-analysis.yaml`. Use it for a pre-downloaded model directory on an offline server or shared compute cluster.

Start the browser client in another terminal:

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm --prefix web run dev -- --host 0.0.0.0
```

## Dispatch Modes

`BADMINTON_DISPATCH_MODE=local` is the default. It processes one analysis at a time in the API host, which must therefore have GPU access.

For a separate GPU worker, set the following before starting the API and worker:

```bash
export BADMINTON_DISPATCH_MODE=celery
export CELERY_BROKER_URL=redis://localhost:6379/0
celery -A badminton_coach_skill.web.worker.celery_app worker --loglevel=INFO
celery -A badminton_coach_skill.web.worker.celery_app beat --loglevel=INFO
```

The worker uses the same environment variables as the API. The periodic Celery task removes expired student media every hour.

## HTTP Interface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/analyses` | Upload a video and create an analysis job. |
| `GET` | `/api/analyses/{analysis_id}` | Read state and progress. |
| `GET` | `/api/analyses/{analysis_id}/report` | Read the completed public-safe report. |
| `GET` | `/api/analyses/{analysis_id}/frames/{asset_id}` | Read a selected student keyframe only. |
| `GET` | `/api/coach-references/{reference_id}/frame` | Read a cached coach reference frame. |
| `DELETE` | `/api/analyses/{analysis_id}` | Delete all private student media immediately. |
| `WS` | `/api/analyses/{analysis_id}/events` | Receive progress updates. |

Student upload requests stream to disk in chunks rather than loading the entire video into API memory.

## Privacy And Media Lifetime

- Original uploads, normalized derivatives, selected student frames, and model intermediates are private deployment media.
- Each analysis has a 24-hour expiry by default.
- Deleting an analysis immediately removes its private media and marks the job expired.
- The application never exposes the original upload through a frame endpoint.
- Coach reference media is downloaded only when needed for a completed diagnostic report, extracted to one cached image, and the temporary source download is removed.
- Git must not contain uploads, frames, model outputs, private caches, database files, logs, or access tokens.

## When A Video Is Not Usable

The Qwen-VL gate may reject all pose candidates when the video contains an explanation shot, static gesture, severe crop, or insufficient action evidence. In that case the report completes without a fabricated diagnosis and returns retake guidance: use a side or rear-side view, keep the full body and racket side visible, and record continuously from movement start through recovery.
