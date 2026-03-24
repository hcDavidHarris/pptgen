"""Run domain models for Stage 6C."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunSource(str, Enum):
    API_SYNC = "api_sync"      # POST /v1/generate
    API_ASYNC = "api_async"    # POST /v1/jobs → worker
    CLI = "cli"
    BATCH = "batch"


@dataclass
class RunRecord:
    run_id: str
    status: RunStatus
    source: RunSource

    job_id: Optional[str] = None
    request_id: Optional[str] = None
    mode: str = "deterministic"
    template_id: Optional[str] = None
    playbook_id: Optional[str] = None
    profile: str = "dev"
    config_fingerprint: Optional[str] = None

    started_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    completed_at: Optional[datetime] = None
    total_ms: Optional[float] = None

    error_category: Optional[str] = None
    error_message: Optional[str] = None

    manifest_path: Optional[str] = None  # relative to artifact_store_base

    stage_timings: Optional[list] = None  # [{"stage": str, "duration_ms": float|None}]
    artifact_count: Optional[int] = None

    @classmethod
    def create(
        cls,
        source: RunSource,
        mode: str = "deterministic",
        run_id: Optional[str] = None,
        job_id: Optional[str] = None,
        request_id: Optional[str] = None,
        template_id: Optional[str] = None,
        profile: str = "dev",
        config_fingerprint: Optional[str] = None,
    ) -> RunRecord:
        return cls(
            run_id=run_id if run_id is not None else uuid.uuid4().hex,
            status=RunStatus.RUNNING,
            source=source,
            job_id=job_id,
            request_id=request_id,
            mode=mode,
            template_id=template_id,
            profile=profile,
            config_fingerprint=config_fingerprint,
        )

    def is_terminal(self) -> bool:
        return self.status in (
            RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED
        )
