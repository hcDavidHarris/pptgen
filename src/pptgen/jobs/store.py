"""Abstract store protocol — implementations in sqlite_store.py."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional, Protocol, runtime_checkable

from .models import JobRecord, JobStatus


@runtime_checkable
class AbstractJobStore(Protocol):
    def submit(self, job: JobRecord) -> None: ...
    def get(self, job_id: str) -> Optional[JobRecord]: ...
    def claim_next(self, worker_id: str) -> Optional[JobRecord]: ...
    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        error_category: Optional[str] = None,
        error_message: Optional[str] = None,
        output_path: Optional[str] = None,
        artifact_paths: Optional[str] = None,
        playbook_id: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> None: ...
    def cancel(self, job_id: str) -> str | None: ...
    def list_jobs(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> list[JobRecord]: ...
    def list_stale_running(self, timeout: timedelta) -> list[JobRecord]: ...
    def job_summary(self) -> dict: ...
    def close(self) -> None: ...
