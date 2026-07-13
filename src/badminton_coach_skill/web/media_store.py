from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Protocol


class AsyncUploadReader(Protocol):
    async def read(self, size: int = -1) -> bytes:
        """Read the next upload chunk."""


class LocalMediaStore:
    """Opaque job-scoped storage for temporary student media only."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id: str) -> Path:
        if not job_id or Path(job_id).name != job_id:
            raise ValueError("job_id must be an opaque path segment")
        return self.root / job_id

    def _target(self, job_id: str, name: str) -> Path:
        if not name or Path(name).name != name:
            raise ValueError("media name must be a file name")
        target = (self.job_dir(job_id) / name).resolve()
        if self.job_dir(job_id).resolve() not in target.parents:
            raise ValueError("media target escapes job directory")
        return target

    def write_bytes(self, job_id: str, name: str, content: bytes) -> str:
        target = self._target(job_id, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.write_bytes(content)
        os.replace(temporary, target)
        return str(target.relative_to(self.root))

    async def write_upload(
        self,
        job_id: str,
        name: str,
        upload: AsyncUploadReader,
        *,
        max_bytes: int,
        chunk_bytes: int = 1024 * 1024,
    ) -> str:
        target = self._target(job_id, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        total = 0
        try:
            with temporary.open("wb") as output:
                while chunk := await upload.read(chunk_bytes):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("Upload exceeds configured upload limit")
                    output.write(chunk)
            if total == 0:
                raise ValueError("Upload is empty")
            os.replace(temporary, target)
            return str(target.relative_to(self.root))
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def resolve_key(self, media_key: str) -> Path:
        target = (self.root / media_key).resolve()
        if self.root not in target.parents:
            raise ValueError("media key escapes store")
        return target

    def delete_job(self, job_id: str) -> None:
        try:
            shutil.rmtree(self.job_dir(job_id))
        except FileNotFoundError:
            return
