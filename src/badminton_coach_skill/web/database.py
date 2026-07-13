from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from ..video_evidence.contracts import CoachReference
from .models import AnalysisEvent, AnalysisJob, JobState, MediaAsset


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


class AnalysisJobRecord(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    coach_id: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    action_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    player_profile: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    failure_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class AnalysisEventRecord(Base):
    __tablename__ = "analysis_events"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MediaAssetRecord(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    media_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class CoachReferenceRecord(Base):
    __tablename__ = "coach_references"

    reference_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    coach_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    availability: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    media_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class Database:
    def __init__(self, database_url: str):
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, future=True, connect_args=connect_args)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self._sessions()

    @staticmethod
    def _job(record: AnalysisJobRecord) -> AnalysisJob:
        return AnalysisJob(
            id=record.id,
            coach_id=record.coach_id,
            state=record.state,  # type: ignore[arg-type]
            progress=record.progress,
            created_at=_as_utc(record.created_at),
            expires_at=_as_utc(record.expires_at),
            action_hint=record.action_hint,
            failure_code=record.failure_code,
        )

    def create_job(self, job: AnalysisJob, player_profile: dict[str, Any]) -> AnalysisJob:
        with self.session() as session:
            session.add(
                AnalysisJobRecord(
                    id=job.id,
                    coach_id=job.coach_id,
                    state=job.state,
                    progress=job.progress,
                    created_at=job.created_at,
                    expires_at=job.expires_at,
                    action_hint=job.action_hint,
                    player_profile=player_profile,
                )
            )
            session.commit()
        return job

    def get_job(self, job_id: str) -> AnalysisJob:
        with self.session() as session:
            record = session.get(AnalysisJobRecord, job_id)
            if record is None:
                raise KeyError(job_id)
            return self._job(record)

    def get_player_profile(self, job_id: str) -> dict[str, Any]:
        with self.session() as session:
            record = session.get(AnalysisJobRecord, job_id)
            if record is None:
                raise KeyError(job_id)
            return dict(record.player_profile or {})

    def get_report(self, job_id: str) -> dict[str, Any] | None:
        with self.session() as session:
            record = session.get(AnalysisJobRecord, job_id)
            if record is None:
                raise KeyError(job_id)
            return record.report

    def save_report(self, job_id: str, report: dict[str, Any]) -> None:
        with self.session() as session:
            record = session.get(AnalysisJobRecord, job_id)
            if record is None:
                raise KeyError(job_id)
            record.report = report
            session.commit()

    def set_state(
        self, job_id: str, state: JobState, progress: int, message: str, failure_code: str | None = None
    ) -> AnalysisJob:
        with self.session() as session:
            record = session.get(AnalysisJobRecord, job_id)
            if record is None:
                raise KeyError(job_id)
            record.state = state
            record.progress = max(0, min(progress, 100))
            record.failure_code = failure_code
            session.add(
                AnalysisEventRecord(
                    job_id=job_id,
                    state=state,
                    progress=record.progress,
                    message=message,
                    created_at=utcnow(),
                )
            )
            session.commit()
            return self._job(record)

    def list_events(self, job_id: str, after_sequence: int = 0) -> list[AnalysisEvent]:
        with self.session() as session:
            records = session.scalars(
                select(AnalysisEventRecord)
                .where(AnalysisEventRecord.job_id == job_id, AnalysisEventRecord.sequence > after_sequence)
                .order_by(AnalysisEventRecord.sequence)
            ).all()
            return [
                AnalysisEvent(
                    sequence=record.sequence,
                    job_id=record.job_id,
                    state=record.state,  # type: ignore[arg-type]
                    progress=record.progress,
                    message=record.message,
                    created_at=_as_utc(record.created_at),
                )
                for record in records
            ]

    def list_expired_jobs(self, now: datetime) -> list[AnalysisJob]:
        with self.session() as session:
            records = session.scalars(
                select(AnalysisJobRecord).where(
                    AnalysisJobRecord.expires_at <= now,
                    AnalysisJobRecord.state.not_in(("expired", "deleting")),
                )
            ).all()
            return [self._job(record) for record in records]

    def add_media_asset(self, asset: MediaAsset) -> None:
        with self.session() as session:
            session.add(
                MediaAssetRecord(
                    id=asset.id,
                    job_id=asset.job_id,
                    media_key=asset.media_key,
                    kind=asset.kind,
                    expires_at=asset.expires_at,
                )
            )
            session.commit()

    def list_media_assets(self, job_id: str, kind: str | None = None) -> list[MediaAsset]:
        with self.session() as session:
            statement = select(MediaAssetRecord).where(MediaAssetRecord.job_id == job_id)
            if kind is not None:
                statement = statement.where(MediaAssetRecord.kind == kind)
            records = session.scalars(statement.order_by(MediaAssetRecord.id)).all()
            return [
                MediaAsset(
                    id=record.id,
                    job_id=record.job_id,
                    media_key=record.media_key,
                    kind=record.kind,  # type: ignore[arg-type]
                    expires_at=_as_utc(record.expires_at),
                )
                for record in records
            ]

    def save_coach_reference(self, reference: CoachReference) -> None:
        with self.session() as session:
            record = session.get(CoachReferenceRecord, reference.reference_id)
            payload = reference.to_dict()
            if record is None:
                session.add(
                    CoachReferenceRecord(
                        reference_id=reference.reference_id,
                        coach_id=reference.coach_id,
                        availability=reference.availability,
                        media_key=reference.media_key,
                        payload=payload,
                    )
                )
            else:
                record.coach_id = reference.coach_id
                record.availability = reference.availability
                record.media_key = reference.media_key
                record.payload = payload
            session.commit()

    def get_coach_reference(self, reference_id: str) -> CoachReference | None:
        with self.session() as session:
            record = session.get(CoachReferenceRecord, reference_id)
            if record is None:
                return None
            payload = record.payload
            return CoachReference(
                reference_id=str(payload["reference_id"]),
                coach_id=str(payload["coach_id"]),
                source_id=str(payload["source_id"]),
                phase=str(payload["phase"]),  # type: ignore[arg-type]
                timestamp_ms=int(payload["timestamp_ms"]),
                source_url=str(payload["source_url"]),
                confidence=str(payload["confidence"]),  # type: ignore[arg-type]
                actions=tuple(str(item) for item in payload.get("actions", [])),
                framework_ids=tuple(str(item) for item in payload.get("framework_ids", [])),
                availability=str(payload["availability"]),  # type: ignore[arg-type]
                media_key=str(payload.get("media_key", "")),
                title=str(payload.get("title", "")),
                window_start_ms=payload.get("window_start_ms"),
                window_end_ms=payload.get("window_end_ms"),
                visible_facts=tuple(str(item) for item in payload.get("visible_facts", [])),
                limitations=tuple(str(item) for item in payload.get("limitations", [])),
            )

    def delete_media_assets(self, job_id: str) -> None:
        with self.session() as session:
            records = session.scalars(
                select(MediaAssetRecord).where(MediaAssetRecord.job_id == job_id)
            ).all()
            for record in records:
                session.delete(record)
            session.commit()

    def find_media_asset(self, job_id: str, asset_id: str) -> MediaAsset | None:
        with self.session() as session:
            record = session.get(MediaAssetRecord, asset_id)
            if record is None or record.job_id != job_id:
                return None
            return MediaAsset(
                id=record.id,
                job_id=record.job_id,
                media_key=record.media_key,
                kind=record.kind,  # type: ignore[arg-type]
                expires_at=_as_utc(record.expires_at),
            )
