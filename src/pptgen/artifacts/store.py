"""Abstract artifact store protocol."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from .models import ArtifactRecord, ArtifactStatus


@runtime_checkable
class AbstractArtifactStore(Protocol):
    def register(self, artifact: ArtifactRecord) -> None: ...
    def get(self, artifact_id: str) -> Optional[ArtifactRecord]: ...
    def list_for_run(self, run_id: str) -> list[ArtifactRecord]: ...
    def update_status(self, artifact_id: str, status: ArtifactStatus) -> None: ...
    def list_expired(
        self,
        retention_class: str,
        cutoff: datetime,
    ) -> list[ArtifactRecord]: ...
    def close(self) -> None: ...
