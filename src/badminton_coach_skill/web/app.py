from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse

from .database import Database
from .jobs import create_analysis_job, delete_analysis_job
from .media_store import LocalMediaStore
from .models import MediaAsset
from .schemas import AnalysisJobResponse, AnalysisReportResponse
from .settings import Settings


def _job_response(job: object) -> AnalysisJobResponse:
    return AnalysisJobResponse(
        analysis_id=job.id,
        state=job.state,
        progress=job.progress,
        expires_at=job.expires_at,
        action_hint=job.action_hint,
        failure_code=job.failure_code,
    )


def _parse_player_profile(raw: str) -> dict[str, object]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=422, detail="player_profile must be JSON") from error
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="player_profile must be a JSON object")
    return parsed


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime = settings or Settings.from_env()
    database = Database(runtime.database_url)
    database.create_all()
    media_store = LocalMediaStore(runtime.media_root)

    app = FastAPI(title="BadmintonCoach Video Evidence API", version="0.2.0")
    app.state.settings = runtime
    app.state.database = database
    app.state.media_store = media_store

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
        payload = await video.read(runtime.max_upload_bytes + 1)
        if len(payload) > runtime.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Video exceeds configured upload limit")
        if not payload:
            raise HTTPException(status_code=422, detail="Video file is empty")

        job = create_analysis_job(database, coach_id, action_hint, profile)
        suffix = Path(video.filename).suffix.lower() or ".mp4"
        media_key = media_store.write_bytes(job.id, f"upload{suffix}", payload)
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
        return _job_response(database.get_job(job.id))

    @app.get("/api/analyses/{analysis_id}", response_model=AnalysisJobResponse)
    def get_analysis(analysis_id: str) -> AnalysisJobResponse:
        try:
            return _job_response(database.get_job(analysis_id))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Analysis not found") from error

    @app.delete("/api/analyses/{analysis_id}", response_model=AnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
    def delete_analysis(analysis_id: str) -> AnalysisJobResponse:
        try:
            return _job_response(delete_analysis_job(database, media_store, analysis_id))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Analysis not found") from error

    @app.get("/api/analyses/{analysis_id}/report", response_model=AnalysisReportResponse)
    def get_report(analysis_id: str) -> AnalysisReportResponse:
        try:
            job = database.get_job(analysis_id)
            report = database.get_report(analysis_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Analysis not found") from error
        if job.state == "expired":
            raise HTTPException(status_code=410, detail="Analysis media has expired")
        if report is None:
            raise HTTPException(status_code=409, detail="Analysis report is not ready")
        return AnalysisReportResponse(report=report)

    @app.get("/api/analyses/{analysis_id}/frames/{asset_id}")
    def get_student_frame(analysis_id: str, asset_id: str) -> FileResponse:
        try:
            job = database.get_job(analysis_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Analysis not found") from error
        if job.state == "expired" or job.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Student media has expired")
        asset = database.find_media_asset(analysis_id, asset_id)
        if asset is None or asset.kind != "student_frame":
            raise HTTPException(status_code=404, detail="Frame not found")
        target = media_store.resolve_key(asset.media_key)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Frame is unavailable")
        return FileResponse(target, headers={"Cache-Control": "private, no-store"})

    @app.websocket("/api/analyses/{analysis_id}/events")
    async def analysis_events(websocket: WebSocket, analysis_id: str) -> None:
        try:
            database.get_job(analysis_id)
        except KeyError:
            await websocket.close(code=4404)
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
