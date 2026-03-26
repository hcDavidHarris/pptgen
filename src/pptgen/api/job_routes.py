"""Async job queue endpoints — Stage 6B."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..jobs.models import JobRecord, WorkloadType
from ..jobs.store import AbstractJobStore
from typing import Optional
from .schemas import JobCancelResponse, JobListResponse, JobStatusResponse, JobSubmitRequest, RunListItemResponse

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


def get_job_store(request: Request) -> AbstractJobStore:
    """FastAPI dependency — reads store from app.state."""
    store = getattr(request.app.state, "job_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Job store not available")
    return store


def _to_status_response(job: JobRecord) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.job_id,
        run_id=job.run_id,
        status=job.status.value,
        workload_type=job.workload_type.value,
        submitted_at=job.submitted_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        retry_count=job.retry_count,
        error_category=job.error_category,
        error_message=job.error_message,
        output_path=job.output_path,
        playbook_id=job.playbook_id,
        action_type=job.action_type,
        source_run_id=job.source_run_id,
    )


@router.get("")
def list_jobs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
) -> JobListResponse:
    """List recent jobs with optional status filter."""
    store = get_job_store(request)
    jobs = store.list_jobs(limit=limit, offset=offset, status=status)
    return JobListResponse(
        jobs=[_to_status_response(j) for j in jobs],
        total=len(jobs),
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=202)
def submit_job(
    body: JobSubmitRequest,
    request: Request,
) -> JobStatusResponse:
    """Submit a presentation generation job to the async queue."""
    store = get_job_store(request)
    try:
        wt = WorkloadType(body.workload_type)
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"Unknown workload_type: {body.workload_type}"
        )

    job = JobRecord.create(
        input_text=body.input_text,
        workload_type=wt,
        mode=body.mode,
        template_id=body.template_id,
        artifacts=body.artifacts,
    )
    store.submit(job)
    return _to_status_response(job)


@router.get("/{job_id}")
def get_job_status(job_id: str, request: Request) -> JobStatusResponse:
    """Poll the status of a submitted job."""
    store = get_job_store(request)
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return _to_status_response(job)


@router.get("/{job_id}/runs")
def get_job_runs(job_id: str, request: Request) -> list[RunListItemResponse]:
    """List all run records linked to a job."""
    store = get_job_store(request)
    if store.get(job_id) is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    run_store = getattr(request.app.state, "run_store", None)
    if run_store is None:
        raise HTTPException(status_code=503, detail="Run store not available")
    runs = run_store.list_for_job(job_id)
    from .run_routes import _run_to_list_item
    return [_run_to_list_item(r) for r in runs]


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, request: Request) -> JobCancelResponse:
    """Cancel a queued, retrying, or running job."""
    store = get_job_store(request)
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job.is_terminal():
        return JobCancelResponse(
            job_id=job_id,
            accepted=False,
            status=job.status.value,
            message=f"Job is already terminal (status='{job.status.value}').",
        )
    new_status = store.cancel(job_id)
    if new_status is None:
        return JobCancelResponse(
            job_id=job_id,
            accepted=False,
            status=job.status.value,
            message=f"Job cannot be cancelled in status '{job.status.value}'.",
        )
    accepted = True
    if new_status == "cancellation_requested":
        message = "Cancellation requested; job will be cancelled after current execution completes."
    else:
        message = "Job cancelled."
    return JobCancelResponse(job_id=job_id, accepted=accepted, status=new_status, message=message)
