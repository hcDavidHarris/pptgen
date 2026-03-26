"""Structured logging utilities for pptgen."""
from __future__ import annotations

import json
import logging
from typing import Any, Optional


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("event", "run_id", "job_id", "component", "metadata"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


class StructuredLogger:
    """Thin wrapper that emits structured log events with consistent extra fields."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def event(
        self,
        event_type: str,
        level: int = logging.INFO,
        run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        component: Optional[str] = None,
        **metadata,
    ) -> None:
        extra: dict[str, Any] = {"event": event_type}
        if run_id is not None:
            extra["run_id"] = run_id
        if job_id is not None:
            extra["job_id"] = job_id
        if component is not None:
            extra["component"] = component
        if metadata:
            extra["metadata"] = metadata
        self._logger.log(level, event_type, extra=extra)

    def run_started(self, run_id: str, source: str, **kw) -> None:
        self.event("run_started", run_id=run_id, source=source, **kw)

    def run_completed(self, run_id: str, total_ms: Optional[float] = None, **kw) -> None:
        self.event("run_completed", run_id=run_id, total_ms=total_ms, **kw)

    def run_failed(self, run_id: str, error_category: Optional[str] = None, **kw) -> None:
        self.event("run_failed", run_id=run_id, error_category=error_category, **kw)

    def job_claimed(self, job_id: str, run_id: str, worker_id: str) -> None:
        self.event("job_claimed", job_id=job_id, run_id=run_id, worker_id=worker_id)

    def job_completed(self, job_id: str, run_id: str, **kw) -> None:
        self.event("job_completed", job_id=job_id, run_id=run_id, **kw)

    def job_failed(self, job_id: str, run_id: str, error: str = "", **kw) -> None:
        self.event("job_failed", logging.WARNING, job_id=job_id, run_id=run_id, error=error, **kw)

    def artifact_promoted(
        self, run_id: str, artifact_type: str, size_bytes: int, checksum: str
    ) -> None:
        self.event(
            "artifact_promoted",
            run_id=run_id,
            artifact_type=artifact_type,
            size_bytes=size_bytes,
            checksum=checksum,
        )

    def template_resolved(
        self,
        template_id: str,
        version: str,
        template_revision_hash: str,
        resolution_mode: str,
        run_id: Optional[str] = None,
    ) -> None:
        self.event(
            "template_resolved",
            run_id=run_id,
            template_id=template_id,
            version=version,
            template_revision_hash=template_revision_hash,
            resolution_mode=resolution_mode,
        )


def get_logger(name: str) -> StructuredLogger:
    """Return a StructuredLogger for the given name."""
    return StructuredLogger(name)
