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
    ) -> None: ...
    def close(self) -> None: ...
