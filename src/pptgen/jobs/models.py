"""Job domain models for Stage 6B durable execution."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    CANCELLATION_REQUESTED = "cancellation_requested"


class WorkloadType(str, Enum):
    INTERACTIVE = "interactive"   # priority 10 — API single-file jobs
    BATCH = "batch"               # priority 0  — bulk submissions


_WORKLOAD_PRIORITY: dict[WorkloadType, int] = {
    WorkloadType.INTERACTIVE: 10,
    WorkloadType.BATCH: 0,
}


@dataclass
class JobRecord:
    job_id: str
    run_id: str
    status: JobStatus
    workload_type: WorkloadType
    priority: int
    input_text: str

    # Optional inputs
    request_id: Optional[str] = None
    mode: str = "deterministic"
    template_id: Optional[str] = None
    artifacts: bool = False

    # Timing
    submitted_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Retry
    retry_count: int = 0
    max_retries: int = 3

    # Result / failure
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    artifact_paths: Optional[str] = None   # JSON-encoded list

    # Internal
    playbook_id: Optional[str] = None
    worker_id: Optional[str] = None
    claimed_at: Optional[datetime] = None

    # Lineage / replay fields
    action_type: Optional[str] = None    # 'retry' | 'rerun' | None
    source_run_id: Optional[str] = None  # run_id this job was derived from

    @classmethod
    def create(
        cls,
        input_text: str,
        workload_type: WorkloadType = WorkloadType.INTERACTIVE,
        mode: str = "deterministic",
        template_id: Optional[str] = None,
        artifacts: bool = False,
        request_id: Optional[str] = None,
        max_retries: int = 3,
        action_type: Optional[str] = None,
        source_run_id: Optional[str] = None,
    ) -> JobRecord:
        job_id = uuid.uuid4().hex
        return cls(
            job_id=job_id,
            run_id=uuid.uuid4().hex,
            status=JobStatus.QUEUED,
            workload_type=workload_type,
            priority=_WORKLOAD_PRIORITY[workload_type],
            input_text=input_text,
            request_id=request_id,
            mode=mode,
            template_id=template_id,
            artifacts=artifacts,
            max_retries=max_retries,
            action_type=action_type,
            source_run_id=source_run_id,
        )

    def is_terminal(self) -> bool:
        return self.status in (
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.TIMED_OUT,
        )

    def is_cancellable(self) -> bool:
        return self.status in (
            JobStatus.QUEUED,
            JobStatus.RETRYING,
            JobStatus.RUNNING,
        )
