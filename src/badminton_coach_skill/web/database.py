from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, create_engine, inspect, select, text, update
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
    access_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")


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
        if self.engine.dialect.name == "sqlite":
            columns = {column["name"] for column in inspect(self.engine).get_columns("analysis_jobs")}
            if "access_token_hash" not in columns:
                with self.engine.begin() as connection:
                    connection.execute(
                        text(
                            "ALTER TABLE analysis_jobs ADD COLUMN access_token_hash "
                            "VARCHAR(64) NOT NULL DEFAULT ''"
                        )
                    )

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

    def create_job(
        self, job: AnalysisJob, player_profile: dict[str, Any], *, access_token: str
    ) -> AnalysisJob:
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
                    access_token_hash=self._token_hash(access_token),
                )
            )
            session.commit()
        return job

    @staticmethod
    def _token_hash(access_token: str) -> str:
        return hashlib.sha256(access_token.encode("utf-8")).hexdigest()

    def has_valid_access_token(self, job_id: str, access_token: str | None) -> bool:
        if not access_token:
            return False
        with self.session() as session:
            record = session.get(AnalysisJobRecord, job_id)
            if record is None or not record.access_token_hash:
                return False
            return hmac.compare_digest(record.access_token_hash, self._token_hash(access_token))

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

    def save_report_if_active(self, job_id: str, report: dict[str, Any]) -> bool:
        """Persist a report only while its job remains active and unexpired."""
        with self.session() as session:
            saved = session.execute(
                update(AnalysisJobRecord)
                .where(
                    AnalysisJobRecord.id == job_id,
                    ~AnalysisJobRecord.state.in_(("deleting", "expired")),
                    AnalysisJobRecord.expires_at > utcnow(),
                )
                .values(report=report)
            )
            if saved.rowcount != 1:
                session.rollback()
                return False
            session.commit()
            return True

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

    def set_active_state(
        self, job_id: str, state: JobState, progress: int, message: str, failure_code: str | None = None
    ) -> AnalysisJob | None:
        """Advance a worker-owned job without reviving deletion or expiry terminal states."""
        with self.session() as session:
            updated = session.execute(
                update(AnalysisJobRecord)
                .where(
                    AnalysisJobRecord.id == job_id,
                    ~AnalysisJobRecord.state.in_(("deleting", "expired")),
                    AnalysisJobRecord.expires_at > utcnow(),
                )
                .values(
                    state=state,
                    progress=max(0, min(progress, 100)),
                    failure_code=failure_code,
                )
            )
            if updated.rowcount != 1:
                session.rollback()
                return None
            record = session.get(AnalysisJobRecord, job_id)
            assert record is not None
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
                select(AnalysisJobRecord).where(AnalysisJobRecord.expires_at <= now)
            ).all()
            return [self._job(record) for record in records]

    def claim_analysis_job(self, job_id: str) -> AnalysisJob | None:
        """Atomically claim an upload or queued job for one worker."""
        with self.session() as session:
            claimed = session.execute(
                update(AnalysisJobRecord)
                .where(
                    AnalysisJobRecord.id == job_id,
                    AnalysisJobRecord.state.in_(("uploaded", "queued")),
                    AnalysisJobRecord.expires_at > utcnow(),
                )
                .values(state="normalizing", progress=8, failure_code=None)
            )
            if claimed.rowcount != 1:
                session.rollback()
                return None
            session.add(
                AnalysisEventRecord(
                    job_id=job_id,
                    state="normalizing",
                    progress=8,
                    message="Preparing uploaded video.",
                    created_at=utcnow(),
                )
            )
            record = session.get(AnalysisJobRecord, job_id)
            assert record is not None
            session.commit()
            return self._job(record)

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

    def job_has_coach_reference(self, job_id: str, reference_id: str) -> bool:
        report = self.get_report(job_id)
        if not report:
            return False
        references = report.get("coach_references", [])
        return any(
            isinstance(reference, dict) and reference.get("reference_id") == reference_id
            for reference in references
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
