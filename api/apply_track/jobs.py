"""In-process store for resume parse jobs.

Single-user app, so a dict behind a lock is enough -- no broker, no extra
process. Jobs are transient by design: the parsed result is handed to the review
screen and only persisted once the user saves it.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

JobStatus = Literal["queued", "running", "done", "error"]

MAX_AGE = timedelta(hours=6)


@dataclass
class Job:
    id: str
    filename: str
    status: JobStatus = "queued"
    error: str = ""
    result: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "error": self.error,
            "result": self.result,
        }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, filename: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:16], filename=filename)
        with self._lock:
            self._prune_locked()
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        self._update(job_id, status="running")

    def mark_done(self, job_id: str, result: dict[str, Any]) -> None:
        self._update(job_id, status="done", result=result)

    def mark_error(self, job_id: str, error: str) -> None:
        self._update(job_id, status="error", error=error)

    def _update(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in changes.items():
                setattr(job, key, value)

    def _prune_locked(self) -> None:
        cutoff = datetime.now(timezone.utc) - MAX_AGE
        for job_id in [j.id for j in self._jobs.values() if j.created_at < cutoff]:
            del self._jobs[job_id]


store = JobStore()
