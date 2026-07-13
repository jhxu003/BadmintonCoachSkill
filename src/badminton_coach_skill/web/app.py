from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse

from .database import Database
from .cleanup import cleanup_expired_jobs
from .dispatch import AnalysisDispatcher, create_dispatcher
from .jobs import create_analysis_job, delete_analysis_job
from .media_store import LocalMediaStore
from .models import AnalysisJob, MediaAsset
from .schemas import AnalysisJobResponse, AnalysisReportResponse
from .settings import Settings


def _job_response(job: AnalysisJob) -> AnalysisJobResponse:
    return AnalysisJobResponse(
        analysis_id=job.id,
        state=job.state,
        progress=job.progress,
        expires_at=job.expires_at,
        action_hint=job.action_hint,
        failure_code=job.failure_code,
        access_token=job.access_token,
    )


def _parse_player_profile(raw: str) -> dict[str, object]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=422, detail="player_profile must be JSON") from error
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="player_profile must be a JSON object")
    return parsed


def create_app(
    settings: Settings | None = None, dispatcher: AnalysisDispatcher | None = None
) -> FastAPI:
    runtime = settings or Settings.from_env()
    database = Database(runtime.database_url)
    database.create_all()
    media_store = LocalMediaStore(runtime.media_root)
    active_dispatcher = dispatcher or create_dispatcher(runtime)
    cleanup_task: asyncio.Task[None] | None = None

    async def cleanup_loop() -> None:
        while True:
            cleanup_expired_jobs(database, media_store)
            await asyncio.sleep(runtime.cleanup_interval_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        nonlocal cleanup_task
        if runtime.dispatch_mode == "local":
            cleanup_task = asyncio.create_task(cleanup_loop())
        try:
            yield
        finally:
            if cleanup_task is not None:
                cleanup_task.cancel()
            close = getattr(active_dispatcher, "close", None)
            if callable(close):
                close()

    app = FastAPI(
        title="BadmintonCoach Video Evidence API", version="0.2.0", lifespan=lifespan
    )
    app.state.settings = runtime
    app.state.database = database
    app.state.media_store = media_store
    app.state.dispatcher = active_dispatcher

    def require_analysis_access(analysis_id: str, access_token: str | None) -> AnalysisJob:
        try:
            job = database.get_job(analysis_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Analysis not found") from error
        if not database.has_valid_access_token(analysis_id, access_token):
            raise HTTPException(status_code=401, detail="Analysis access token is required")
        return job

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/analyses", response_model=AnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
    async def create_analysis(
        video: UploadFile = File(...),
        coach_id: str = Form(...),
        action_hint: str | None = Form(None),
        player_profile: str = Form("{}"),
    ) -> AnalysisJobResponse:
        if coach_id not in {"liu-hui", "li-yuxuan"}:
            raise HTTPException(status_code=422, detail="Unsupported coach_id")
        if not video.filename:
            raise HTTPException(status_code=422, detail="A video file is required")
        if not video.content_type or not video.content_type.startswith("video/"):
            raise HTTPException(
                status_code=415, detail="Upload must use a video MIME type"
            )
        profile = _parse_player_profile(player_profile)
        job = create_analysis_job(
            database, coach_id, action_hint, profile, ttl=runtime.analysis_ttl
        )
        suffix = Path(video.filename).suffix.lower() or ".mp4"
        try:
            media_key = await media_store.write_upload(
                job.id,
                f"upload{suffix}",
                video,
                max_bytes=runtime.max_upload_bytes,
            )
        except ValueError as error:
            delete_analysis_job(database, media_store, job.id)
            status_code = 413 if "limit" in str(error).lower() else 422
            raise HTTPException(status_code=status_code, detail=str(error)) from error
        database.add_media_asset(
            MediaAsset(
                id=str(uuid4()),
                job_id=job.id,
                media_key=media_key,
                kind="upload",
                expires_at=job.expires_at,
            )
        )
        database.set_state(job.id, "queued", 2, "Video queued for analysis.")
        try:
            app.state.dispatcher.enqueue(job.id)
        except Exception as error:
            database.set_state(
                job.id,
                "failed",
                2,
                "Analysis worker is unavailable. Please try again later.",
                failure_code=type(error).__name__,
            )
            raise HTTPException(status_code=503, detail="Analysis worker is unavailable") from error
        return _job_response(replace(database.get_job(job.id), access_token=job.access_token))

    @app.get("/api/analyses/{analysis_id}", response_model=AnalysisJobResponse)
    def get_analysis(
        analysis_id: str, x_analysis_token: str | None = Header(default=None)
    ) -> AnalysisJobResponse:
        return _job_response(require_analysis_access(analysis_id, x_analysis_token))

    @app.delete("/api/analyses/{analysis_id}", response_model=AnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
    def delete_analysis(
        analysis_id: str, x_analysis_token: str | None = Header(default=None)
    ) -> AnalysisJobResponse:
        require_analysis_access(analysis_id, x_analysis_token)
        return _job_response(delete_analysis_job(database, media_store, analysis_id))

    @app.get("/api/analyses/{analysis_id}/report", response_model=AnalysisReportResponse)
    def get_report(
        analysis_id: str, x_analysis_token: str | None = Header(default=None)
    ) -> AnalysisReportResponse:
        job = require_analysis_access(analysis_id, x_analysis_token)
        report = database.get_report(analysis_id)
        if job.state == "expired":
            raise HTTPException(status_code=410, detail="Analysis media has expired")
        if report is None:
            raise HTTPException(status_code=409, detail="Analysis report is not ready")
        return AnalysisReportResponse(report=report)

    @app.get("/api/analyses/{analysis_id}/frames/{asset_id}")
    def get_student_frame(
        analysis_id: str,
        asset_id: str,
        access_token: str | None = None,
        x_analysis_token: str | None = Header(default=None),
    ) -> FileResponse:
        job = require_analysis_access(analysis_id, x_analysis_token or access_token)
        if job.state == "expired" or job.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Student media has expired")
        asset = database.find_media_asset(analysis_id, asset_id)
        if asset is None or asset.kind != "student_frame":
            raise HTTPException(status_code=404, detail="Frame not found")
        target = media_store.resolve_key(asset.media_key)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Frame is unavailable")
        return FileResponse(target, headers={"Cache-Control": "private, no-store"})

    @app.get("/api/coach-references/{reference_id}/frame")
    def get_coach_reference_frame(
        reference_id: str,
        analysis_id: str,
        access_token: str | None = None,
        x_analysis_token: str | None = Header(default=None),
    ) -> FileResponse:
        require_analysis_access(analysis_id, x_analysis_token or access_token)
        if not database.job_has_coach_reference(analysis_id, reference_id):
            raise HTTPException(status_code=404, detail="Coach reference frame is unavailable")
        reference = database.get_coach_reference(reference_id)
        if reference is None or reference.availability != "cached" or not reference.media_key:
            raise HTTPException(status_code=404, detail="Coach reference frame is unavailable")
        target = (runtime.coach_media_root / reference.media_key).resolve()
        cache_root = runtime.coach_media_root.resolve()
        if cache_root not in target.parents or not target.is_file():
            raise HTTPException(status_code=404, detail="Coach reference frame is unavailable")
        return FileResponse(target, headers={"Cache-Control": "private, no-store"})

    @app.websocket("/api/analyses/{analysis_id}/events")
    async def analysis_events(
        websocket: WebSocket, analysis_id: str, access_token: str | None = None
    ) -> None:
        try:
            require_analysis_access(analysis_id, access_token)
        except HTTPException as error:
            await websocket.close(code=4401 if error.status_code == 401 else 4404)
            return
        await websocket.accept()
        sequence = 0
        try:
            while True:
                events = database.list_events(analysis_id, sequence)
                for event in events:
                    sequence = event.sequence
                    await websocket.send_json(
                        {
                            "sequence": event.sequence,
                            "state": event.state,
                            "progress": event.progress,
                            "message": event.message,
                            "created_at": event.created_at.isoformat(),
                        }
                    )
                await asyncio.sleep(runtime.websocket_poll_seconds)
        except WebSocketDisconnect:
            return

    return app
