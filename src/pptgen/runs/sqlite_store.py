"""SQLite-backed run registry."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import RunRecord, RunSource, RunStatus

_CREATE_RUNS = """
CREATE TABLE IF NOT EXISTS runs (
    run_id              TEXT PRIMARY KEY,
    status              TEXT NOT NULL,
    source              TEXT NOT NULL,
    job_id              TEXT,
    request_id          TEXT,
    mode                TEXT NOT NULL DEFAULT 'deterministic',
    template_id         TEXT,
    playbook_id         TEXT,
    profile             TEXT NOT NULL DEFAULT 'dev',
    config_fingerprint  TEXT,
    started_at          TEXT NOT NULL,
    completed_at        TEXT,
    total_ms            REAL,
    error_category      TEXT,
    error_message       TEXT,
    manifest_path       TEXT
)
"""


def _dt(v: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None


def _iso(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


def _row_to_run(r: sqlite3.Row) -> RunRecord:
    return RunRecord(
        run_id=r["run_id"],
        status=RunStatus(r["status"]),
        source=RunSource(r["source"]),
        job_id=r["job_id"],
        request_id=r["request_id"],
        mode=r["mode"],
        template_id=r["template_id"],
        playbook_id=r["playbook_id"],
        profile=r["profile"],
        config_fingerprint=r["config_fingerprint"],
        started_at=_dt(r["started_at"]) or datetime.now(tz=timezone.utc),
        completed_at=_dt(r["completed_at"]),
        total_ms=r["total_ms"],
        error_category=r["error_category"],
        error_message=r["error_message"],
        manifest_path=r["manifest_path"],
    )


class SQLiteRunStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_RUNS)
        self._conn.commit()

    def create(self, run: RunRecord) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO runs (run_id, status, source, job_id, request_id,
                   mode, template_id, playbook_id, profile, config_fingerprint,
                   started_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (run.run_id, run.status.value, run.source.value, run.job_id,
                 run.request_id, run.mode, run.template_id, run.playbook_id,
                 run.profile, run.config_fingerprint, _iso(run.started_at)),
            )
            self._conn.commit()

    def get(self, run_id: str) -> Optional[RunRecord]:
        row = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return _row_to_run(row) if row else None

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
    ) -> None:
        terminal = status in (
            RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED
        )
        now = _iso(datetime.now(tz=timezone.utc))
        with self._lock:
            self._conn.execute(
                """UPDATE runs SET
                    status = ?,
                    completed_at = CASE WHEN ? THEN ? ELSE completed_at END,
                    playbook_id = COALESCE(?, playbook_id),
                    error_category = COALESCE(?, error_category),
                    error_message = COALESCE(?, error_message),
                    total_ms = COALESCE(?, total_ms),
                    manifest_path = COALESCE(?, manifest_path)
                WHERE run_id = ?""",
                (status.value, int(terminal), now,
                 playbook_id, error_category, error_message,
                 total_ms, manifest_path, run_id),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @classmethod
    def from_settings(cls, settings) -> SQLiteRunStore:
        return cls(db_path=settings.artifact_db_file)
