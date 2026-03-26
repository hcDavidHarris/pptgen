"""Abstract run store protocol."""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from .models import RunRecord, RunStatus


@runtime_checkable
class AbstractRunStore(Protocol):
    def create(self, run: RunRecord) -> None: ...
    def get(self, run_id: str) -> Optional[RunRecord]: ...
    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        playbook_id: Optional[str] = None,
        error_category: Optional[str] = None,
        error_message: Optional[str] = None,
        total_ms: Optional[float] = None,
        manifest_path: Optional[str] = None,
        stage_timings: Optional[list] = None,
        artifact_count: Optional[int] = None,
    ) -> None: ...
    def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        source: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> list[RunRecord]: ...
    def list_for_job(self, job_id: str) -> list[RunRecord]: ...
    def run_stats(self, since_iso: str) -> dict: ...
    def close(self) -> None: ...
