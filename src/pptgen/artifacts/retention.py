"""Artifact retention policy enforcement."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from .models import ArtifactRetentionClass, ArtifactStatus
from .sqlite_store import SQLiteArtifactStore
from .storage import ArtifactStorage

logger = logging.getLogger(__name__)


class RetentionManager:
    """Marks expired artifacts and deletes their files."""

    def __init__(
        self,
        artifact_store: SQLiteArtifactStore,
        artifact_storage: ArtifactStorage,
    ) -> None:
        self._store = artifact_store
        self._storage = artifact_storage

    def run_cleanup(
        self,
        longest_hours: int,
        medium_hours: int,
        shorter_hours: int,
    ) -> dict[str, int]:
        """Expire artifacts past their retention window.

        Returns counts by retention class.
        ALWAYS class is never expired.
        """
        now = datetime.now(tz=timezone.utc)
        policy = {
            ArtifactRetentionClass.LONGEST.value: timedelta(hours=longest_hours),
            ArtifactRetentionClass.MEDIUM.value: timedelta(hours=medium_hours),
            ArtifactRetentionClass.SHORTER.value: timedelta(hours=shorter_hours),
        }
        counts: dict[str, int] = {}
        for cls_val, delta in policy.items():
            cutoff = now - delta
            expired = self._store.list_expired(cls_val, cutoff)
            for artifact in expired:
                abs_path = self._storage.resolve(artifact.relative_path)
                try:
                    if abs_path.exists():
                        abs_path.unlink()
                    self._store.update_status(
                        artifact.artifact_id, ArtifactStatus.EXPIRED
                    )
                    logger.info(
                        "Expired artifact %s (%s)", artifact.artifact_id, artifact.filename
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to expire artifact %s: %s", artifact.artifact_id, exc
                    )
            counts[cls_val] = len(expired)
        return counts

    @classmethod
    def from_settings(cls, settings, artifact_store, artifact_storage) -> RetentionManager:
        return cls(artifact_store=artifact_store, artifact_storage=artifact_storage)
