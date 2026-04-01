"""SQLite-backed run registry."""
from __future__ import annotations

import json
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
    keys = r.keys()
    stage_timings_raw = r["stage_timings"] if "stage_timings" in keys else None
    stage_timings = json.loads(stage_timings_raw) if stage_timings_raw else None
    artifact_count = r["artifact_count"] if "artifact_count" in keys else None
    input_text = r["input_text"] if "input_text" in keys else None
    action_type = r["action_type"] if "action_type" in keys else None
    source_run_id = r["source_run_id"] if "source_run_id" in keys else None
    template_version = r["template_version"] if "template_version" in keys else None
    template_revision_hash = r["template_revision_hash"] if "template_revision_hash" in keys else None
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
        stage_timings=stage_timings,
        artifact_count=artifact_count,
        input_text=input_text,
        action_type=action_type,
        source_run_id=source_run_id,
        template_version=template_version,
        template_revision_hash=template_revision_hash,
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
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        existing = {row[1] for row in self._conn.execute("PRAGMA table_info(runs)").fetchall()}
        new_columns = {
            "stage_timings":          "ALTER TABLE runs ADD COLUMN stage_timings TEXT",
            "artifact_count":         "ALTER TABLE runs ADD COLUMN artifact_count INTEGER",
            "input_text":             "ALTER TABLE runs ADD COLUMN input_text TEXT",
            "action_type":            "ALTER TABLE runs ADD COLUMN action_type TEXT",
            "source_run_id":          "ALTER TABLE runs ADD COLUMN source_run_id TEXT",
            "template_version":       "ALTER TABLE runs ADD COLUMN template_version TEXT",
            "template_revision_hash": "ALTER TABLE runs ADD COLUMN template_revision_hash TEXT",
        }
        for col, ddl in new_columns.items():
            if col not in existing:
                self._conn.execute(ddl)
        self._conn.commit()

    def create(self, run: RunRecord) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO runs (run_id, status, source, job_id, request_id,
                   mode, template_id, playbook_id, profile, config_fingerprint,
                   started_at, input_text, action_type, source_run_id,
                   template_version, template_revision_hash)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run.run_id, run.status.value, run.source.value, run.job_id,
                 run.request_id, run.mode, run.template_id, run.playbook_id,
                 run.profile, run.config_fingerprint, _iso(run.started_at),
                 run.input_text, run.action_type, run.source_run_id,
                 run.template_version, run.template_revision_hash),
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
        stage_timings: Optional[list] = None,
        artifact_count: Optional[int] = None,
    ) -> None:
        terminal = status in (
            RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED
        )
        now = _iso(datetime.now(tz=timezone.utc))
        stage_timings_json = json.dumps(stage_timings) if stage_timings is not None else None
        with self._lock:
            self._conn.execute(
                """UPDATE runs SET
                    status = ?,
                    completed_at = CASE WHEN ? THEN ? ELSE completed_at END,
                    playbook_id = COALESCE(?, playbook_id),
                    error_category = COALESCE(?, error_category),
                    error_message = COALESCE(?, error_message),
                    total_ms = COALESCE(?, total_ms),
                    manifest_path = COALESCE(?, manifest_path),
                    stage_timings = COALESCE(?, stage_timings),
                    artifact_count = COALESCE(?, artifact_count)
                WHERE run_id = ?""",
                (status.value, int(terminal), now,
                 playbook_id, error_category, error_message,
                 total_ms, manifest_path, stage_timings_json, artifact_count, run_id),
            )
            self._conn.commit()

    def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        source: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> list[RunRecord]:
        clauses: list[str] = []
        params: list = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if source:
            clauses.append("source = ?")
            params.append(source)
        if mode:
            clauses.append("mode = ?")
            params.append(mode)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM runs {where} ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        return [_row_to_run(r) for r in rows]

    def list_for_job(self, job_id: str) -> list[RunRecord]:
        rows = self._conn.execute(
            "SELECT * FROM runs WHERE job_id = ? ORDER BY started_at", (job_id,)
        ).fetchall()
        return [_row_to_run(r) for r in rows]

    def list_runs_by_template(
        self,
        template_id: str,
        template_version: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        since_iso: Optional[str] = None,
    ) -> list[RunRecord]:
        clauses: list[str] = ["template_id = ?"]
        params: list = [template_id]
        if template_version:
            clauses.append("template_version = ?")
            params.append(template_version)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if since_iso:
            clauses.append("started_at >= ?")
            params.append(since_iso)
        where = "WHERE " + " AND ".join(clauses)
        rows = self._conn.execute(
            f"SELECT * FROM runs {where} ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        return [_row_to_run(r) for r in rows]

    def run_stats(self, since_iso: str) -> dict:
        """Return aggregate run counts for runs started after since_iso."""
        row = self._conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) AS succeeded,
                SUM(CASE WHEN status = 'failed'    THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN status = 'running'   THEN 1 ELSE 0 END) AS running,
                AVG(CASE WHEN total_ms > 0 THEN total_ms ELSE NULL END) AS avg_ms
            FROM runs
            WHERE started_at > ?
            """,
            (since_iso,),
        ).fetchone()
        total = row["total"] or 0
        return {
            "total": total,
            "succeeded": row["succeeded"] or 0,
            "failed": row["failed"] or 0,
            "running": row["running"] or 0,
            "avg_ms": row["avg_ms"],
        }

    # ------------------------------------------------------------------
    # Template analytics queries
    # ------------------------------------------------------------------

    def _since_iso(self, days: int) -> str:
        from datetime import timedelta
        return (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()

    def get_template_usage_summary(self, template_id: str, days: int = 30) -> dict:
        """Return aggregate run counts for *template_id* over the last *days* days."""
        since = self._since_iso(days)
        row = self._conn.execute(
            """
            SELECT
                COUNT(*)                                                          AS total_runs,
                SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END)            AS completed_runs,
                SUM(CASE WHEN status = 'failed'    THEN 1 ELSE 0 END)            AS failed_runs,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END)            AS cancelled_runs
            FROM runs
            WHERE template_id = ?
              AND started_at >= ?
            """,
            (template_id, since),
        ).fetchone()
        total = row["total_runs"] or 0
        failed = row["failed_runs"] or 0
        return {
            "template_id": template_id,
            "date_window_days": days,
            "total_runs": total,
            "completed_runs": row["completed_runs"] or 0,
            "failed_runs": failed,
            "cancelled_runs": row["cancelled_runs"] or 0,
            "failure_rate": round(failed / total, 4) if total > 0 else None,
        }

    def get_template_version_usage(self, template_id: str, days: int = 30) -> list[dict]:
        """Return per-version run counts for *template_id* over the last *days* days."""
        since = self._since_iso(days)
        rows = self._conn.execute(
            """
            SELECT
                template_version,
                COUNT(*)                                                       AS total_runs,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)            AS failed_runs,
                MIN(started_at)                                                AS first_seen_at,
                MAX(started_at)                                                AS last_seen_at
            FROM runs
            WHERE template_id = ?
              AND started_at >= ?
              AND template_version IS NOT NULL
            GROUP BY template_version
            ORDER BY total_runs DESC
            """,
            (template_id, since),
        ).fetchall()
        result = []
        for r in rows:
            total = r["total_runs"] or 0
            failed = r["failed_runs"] or 0
            result.append({
                "template_version": r["template_version"],
                "total_runs": total,
                "failed_runs": failed,
                "failure_rate": round(failed / total, 4) if total > 0 else None,
                "first_seen_at": r["first_seen_at"],
                "last_seen_at": r["last_seen_at"],
            })
        return result

    def get_template_usage_trend(self, template_id: str, days: int = 30) -> list[dict]:
        """Return daily run counts per version for *template_id* over the last *days* days."""
        since = self._since_iso(days)
        rows = self._conn.execute(
            """
            SELECT
                DATE(started_at) AS date,
                template_version,
                COUNT(*)         AS run_count
            FROM runs
            WHERE template_id = ?
              AND started_at >= ?
              AND template_version IS NOT NULL
            GROUP BY DATE(started_at), template_version
            ORDER BY date ASC, template_version
            """,
            (template_id, since),
        ).fetchall()
        return [
            {
                "date": r["date"],
                "template_version": r["template_version"],
                "run_count": r["run_count"],
            }
            for r in rows
        ]

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @classmethod
    def from_settings(cls, settings) -> SQLiteRunStore:
        return cls(db_path=settings.artifact_db_file)
