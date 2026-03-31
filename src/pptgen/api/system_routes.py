"""System health endpoint — Phase 7 Stage 2 PR 4."""
from __future__ import annotations

from fastapi import APIRouter, Request

from .schemas import SystemHealthResponse

router = APIRouter(prefix="/v1/system", tags=["system"])


@router.get("/health")
def get_system_health(request: Request) -> SystemHealthResponse:
    job_store = getattr(request.app.state, "job_store", None)
    run_store = getattr(request.app.state, "run_store", None)

    job_store_ok = job_store is not None
    run_store_ok = run_store is not None

    queued = 0
    running = 0
    failed_1h = 0

    if job_store_ok:
        try:
            summary = job_store.job_summary()
            queued = summary.get("queued", 0)
            running = summary.get("running", 0)
            failed_1h = summary.get("failed_1h", 0)
        except Exception:
            job_store_ok = False

    if run_store_ok:
        try:
            # Lightweight check — verify the store is queryable
            run_store.run_stats("9999-01-01T00:00:00")
        except Exception:
            run_store_ok = False

    status = "healthy" if (job_store_ok and run_store_ok) else "degraded"

    return SystemHealthResponse(
        status=status,
        queued_jobs=queued,
        running_jobs=running,
        failed_jobs_1h=failed_1h,
        run_store_ok=run_store_ok,
        job_store_ok=job_store_ok,
    )
