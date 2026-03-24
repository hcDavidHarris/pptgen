"""SQLite-backed job store. WAL mode, thread-safe via threading.Lock."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .models import JobRecord, JobStatus, WorkloadType

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id              TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    status              TEXT NOT NULL,
    workload_type       TEXT NOT NULL,
    priority            INTEGER NOT NULL,
    input_text          TEXT NOT NULL,
    request_id          TEXT,
    mode                TEXT NOT NULL DEFAULT 'deterministic',
    template_id         TEXT,
    artifacts           INTEGER NOT NULL DEFAULT 0,
    submitted_at        TEXT NOT NULL,
    started_at          TEXT,
    completed_at        TEXT,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    max_retries         INTEGER NOT NULL DEFAULT 3,
    error_category      TEXT,
    error_message       TEXT,
    output_path         TEXT,
    artifact_paths      TEXT,
    playbook_id         TEXT,
    worker_id           TEXT,
    claimed_at          TEXT
)
"""


def _dt(val: Optional[str]) -> Optional[datetime]:
    if val is None:
        return None
    return datetime.fromisoformat(val)


def _iso(val: Optional[datetime]) -> Optional[str]:
    if val is None:
        return None
    return val.isoformat()


def _row_to_job(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        job_id=row["job_id"],
        run_id=row["run_id"],
        status=JobStatus(row["status"]),
        workload_type=WorkloadType(row["workload_type"]),
        priority=row["priority"],
        input_text=row["input_text"],
        request_id=row["request_id"],
        mode=row["mode"],
        template_id=row["template_id"],
        artifacts=bool(row["artifacts"]),
        submitted_at=_dt(row["submitted_at"]) or datetime.now(tz=timezone.utc),
        started_at=_dt(row["started_at"]),
        completed_at=_dt(row["completed_at"]),
        retry_count=row["retry_count"],
        max_retries=row["max_retries"],
        error_category=row["error_category"],
        error_message=row["error_message"],
        output_path=row["output_path"],
        artifact_paths=row["artifact_paths"],
        playbook_id=row["playbook_id"],
        worker_id=row["worker_id"],
        claimed_at=_dt(row["claimed_at"]),
    )


class SQLiteJobStore:
    """Thread-safe SQLite job store.

    Uses WAL mode for concurrent read performance and a threading.Lock
    for write serialization within the process.
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    # ------------------------------------------------------------------
    # AbstractJobStore protocol
    # ------------------------------------------------------------------

    def submit(self, job: JobRecord) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO jobs (
                    job_id, run_id, status, workload_type, priority,
                    input_text, request_id, mode, template_id, artifacts,
                    submitted_at, retry_count, max_retries
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    job.job_id, job.run_id, job.status.value,
                    job.workload_type.value, job.priority,
                    job.input_text, job.request_id, job.mode,
                    job.template_id, int(job.artifacts),
                    _iso(job.submitted_at), job.retry_count, job.max_retries,
                ),
            )
            self._conn.commit()

    def get(self, job_id: str) -> Optional[JobRecord]:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return _row_to_job(row) if row else None

    def claim_next(self, worker_id: str) -> Optional[JobRecord]:
        """Atomically claim the highest-priority queued job."""
        with self._lock:
            row = self._conn.execute(
                """
                SELECT * FROM jobs
                WHERE status IN ('queued', 'retrying')
                ORDER BY priority DESC, submitted_at ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            job_id = row["job_id"]
            now = _iso(datetime.now(tz=timezone.utc))
            updated = self._conn.execute(
                """
                UPDATE jobs
                SET status = 'running',
                    worker_id = ?,
                    claimed_at = ?,
                    started_at = COALESCE(started_at, ?)
                WHERE job_id = ? AND status IN ('queued', 'retrying')
                """,
                (worker_id, now, now, job_id),
            ).rowcount
            self._conn.commit()
            if updated == 0:
                return None  # lost the race
            return self.get(job_id)

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
    ) -> None:
        now = _iso(datetime.now(tz=timezone.utc))
        terminal = status in (
            JobStatus.SUCCEEDED, JobStatus.FAILED,
            JobStatus.CANCELLED, JobStatus.TIMED_OUT,
        )
        with self._lock:
            self._conn.execute(
                """
                UPDATE jobs SET
                    status = ?,
                    completed_at = CASE WHEN ? THEN ? ELSE completed_at END,
                    error_category = COALESCE(?, error_category),
                    error_message = COALESCE(?, error_message),
                    output_path = COALESCE(?, output_path),
                    artifact_paths = COALESCE(?, artifact_paths),
                    playbook_id = COALESCE(?, playbook_id),
                    retry_count = COALESCE(?, retry_count)
                WHERE job_id = ?
                """,
                (
                    status.value,
                    int(terminal), now,
                    error_category, error_message,
                    output_path, artifact_paths,
                    playbook_id, retry_count,
                    job_id,
                ),
            )
            self._conn.commit()

    def cancel(self, job_id: str) -> bool:
        """Cancel a queued or retrying job. Returns True if cancelled."""
        with self._lock:
            updated = self._conn.execute(
                """
                UPDATE jobs SET status = 'cancelled', completed_at = ?
                WHERE job_id = ? AND status IN ('queued', 'retrying')
                """,
                (_iso(datetime.now(tz=timezone.utc)), job_id),
            ).rowcount
            self._conn.commit()
        return updated > 0

    def list_stale_running(self, timeout: timedelta) -> list[JobRecord]:
        cutoff = _iso(datetime.now(tz=timezone.utc) - timeout)
        rows = self._conn.execute(
            """
            SELECT * FROM jobs
            WHERE status = 'running' AND claimed_at < ?
            """,
            (cutoff,),
        ).fetchall()
        return [_row_to_job(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @classmethod
    def from_settings(cls, settings) -> SQLiteJobStore:  # RuntimeSettings
        return cls(db_path=settings.job_db_file)
