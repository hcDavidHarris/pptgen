"""SQLite-backed artifact registry."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import (
    ArtifactRecord,
    ArtifactRetentionClass,
    ArtifactStatus,
    ArtifactType,
    ArtifactVisibility,
)

_CREATE_ARTIFACTS = """
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id         TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    artifact_type       TEXT NOT NULL,
    filename            TEXT NOT NULL,
    relative_path       TEXT NOT NULL,
    mime_type           TEXT NOT NULL,
    size_bytes          INTEGER NOT NULL,
    checksum            TEXT NOT NULL,
    is_final_output     INTEGER NOT NULL DEFAULT 0,
    visibility          TEXT NOT NULL,
    retention_class     TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'present',
    created_at          TEXT NOT NULL
)
"""


def _dt(v: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None


def _iso(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


def _row_to_artifact(r: sqlite3.Row) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=r["artifact_id"],
        run_id=r["run_id"],
        artifact_type=ArtifactType(r["artifact_type"]),
        filename=r["filename"],
        relative_path=r["relative_path"],
        mime_type=r["mime_type"],
        size_bytes=r["size_bytes"],
        checksum=r["checksum"],
        is_final_output=bool(r["is_final_output"]),
        visibility=ArtifactVisibility(r["visibility"]),
        retention_class=ArtifactRetentionClass(r["retention_class"]),
        status=ArtifactStatus(r["status"]),
        created_at=_dt(r["created_at"]) or datetime.now(tz=timezone.utc),
    )


class SQLiteArtifactStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_ARTIFACTS)
        self._conn.commit()

    def register(self, artifact: ArtifactRecord) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO artifacts (artifact_id, run_id, artifact_type,
                   filename, relative_path, mime_type, size_bytes, checksum,
                   is_final_output, visibility, retention_class, status,
                   created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (artifact.artifact_id, artifact.run_id, artifact.artifact_type.value,
                 artifact.filename, artifact.relative_path, artifact.mime_type,
                 artifact.size_bytes, artifact.checksum, int(artifact.is_final_output),
                 artifact.visibility.value, artifact.retention_class.value,
                 artifact.status.value, _iso(artifact.created_at)),
            )
            self._conn.commit()

    def get(self, artifact_id: str) -> Optional[ArtifactRecord]:
        row = self._conn.execute(
            "SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        return _row_to_artifact(row) if row else None

    def list_for_run(self, run_id: str) -> list[ArtifactRecord]:
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        return [_row_to_artifact(r) for r in rows]

    def update_status(self, artifact_id: str, status: ArtifactStatus) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE artifacts SET status = ? WHERE artifact_id = ?",
                (status.value, artifact_id),
            )
            self._conn.commit()

    def list_expired(
        self, retention_class: str, cutoff: datetime
    ) -> list[ArtifactRecord]:
        """Return present artifacts of the given class older than cutoff."""
        rows = self._conn.execute(
            """SELECT * FROM artifacts
               WHERE retention_class = ? AND status = 'present'
               AND created_at < ?""",
            (retention_class, _iso(cutoff)),
        ).fetchall()
        return [_row_to_artifact(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @classmethod
    def from_settings(cls, settings) -> SQLiteArtifactStore:
        return cls(db_path=settings.artifact_db_file)
