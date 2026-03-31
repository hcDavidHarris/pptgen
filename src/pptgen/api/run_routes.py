"""Run inspection endpoints — Stage 6C."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from typing import Optional

from ..runs.models import RunRecord, RunSource, RunStatus
from .schemas import (
    ArtifactMetadataResponse,
    RunActionResponse,
    RunListItemResponse,
    RunListResponse,
    RunMetricsResponse,
    RunResponse,
    RunStatsResponse,
)

router = APIRouter(prefix="/v1/runs", tags=["runs"])


def _get_run_store(request: Request):
    store = getattr(request.app.state, "run_store", None)
    if store is None:
        raise HTTPException(503, "Run store not available")
    return store


def _get_artifact_store(request: Request):
    store = getattr(request.app.state, "artifact_store", None)
    if store is None:
        raise HTTPException(503, "Artifact store not available")
    return store


def _get_job_store_optional(request: Request):
    return getattr(request.app.state, "job_store", None)


def _resolve_replay_input(run: RunRecord, job_store) -> Optional[str]:
    """Return the input_text needed to replay this run, or None if unavailable."""
    if run.input_text:
        return run.input_text
    if run.job_id and job_store is not None:
        job = job_store.get(run.job_id)
        if job is not None:
            return job.input_text
    return None


def _get_artifact_storage(request: Request):
    s = getattr(request.app.state, "artifact_storage", None)
    if s is None:
        raise HTTPException(503, "Artifact storage not available")
    return s


def _run_to_response(run: RunRecord, replay_available: bool = False) -> RunResponse:
    return RunResponse(
        run_id=run.run_id,
        status=run.status.value,
        source=run.source.value,
        job_id=run.job_id,
        request_id=run.request_id,
        mode=run.mode,
        template_id=run.template_id,
        playbook_id=run.playbook_id,
        profile=run.profile,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        total_ms=run.total_ms,
        error_category=run.error_category,
        error_message=run.error_message,
        manifest_path=run.manifest_path,
        replay_available=replay_available,
        action_type=run.action_type,
        source_run_id=run.source_run_id,
        template_version=run.template_version,
        template_revision_hash=run.template_revision_hash,
    )


def _run_to_list_item(run: RunRecord) -> RunListItemResponse:
    return RunListItemResponse(
        run_id=run.run_id,
        status=run.status.value,
        source=run.source.value,
        job_id=run.job_id,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        total_ms=run.total_ms,
        artifact_count=run.artifact_count,
        error_category=run.error_category,
        mode=run.mode,
        template_id=run.template_id,
        playbook_id=run.playbook_id,
    )


def _artifact_to_response(a) -> ArtifactMetadataResponse:
    return ArtifactMetadataResponse(
        artifact_id=a.artifact_id,
        run_id=a.run_id,
        artifact_type=a.artifact_type.value,
        filename=a.filename,
        relative_path=a.relative_path,
        mime_type=a.mime_type,
        size_bytes=a.size_bytes,
        checksum=a.checksum,
        is_final_output=a.is_final_output,
        visibility=a.visibility.value,
        retention_class=a.retention_class.value,
        status=a.status.value,
        created_at=a.created_at.isoformat(),
    )


@router.get("")
def list_runs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    source: Optional[str] = None,
    mode: Optional[str] = None,
) -> RunListResponse:
    run_store = _get_run_store(request)
    runs = run_store.list_runs(limit=limit, offset=offset, status=status, source=source, mode=mode)
    return RunListResponse(
        runs=[_run_to_list_item(r) for r in runs],
        total=len(runs),
        limit=limit,
        offset=offset,
    )


_WINDOW_MAP: dict[str, int] = {"1h": 1, "24h": 24, "7d": 168}


@router.get("/stats")          # MUST be registered before /{run_id}
def get_run_stats(
    request: Request,
    window: str = "24h",
) -> RunStatsResponse:
    run_store = _get_run_store(request)
    hours = _WINDOW_MAP.get(window, 24)
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    d = run_store.run_stats(since.isoformat())
    total = d["total"]
    success_rate = round(d["succeeded"] / total * 100, 1) if total > 0 else None
    return RunStatsResponse(
        window_hours=hours,
        total_runs=total,
        succeeded_runs=d["succeeded"],
        failed_runs=d["failed"],
        running_runs=d["running"],
        success_rate=success_rate,
        avg_duration_ms=d["avg_ms"],
    )


@router.get("/{run_id}/metrics")
def get_run_metrics(run_id: str, request: Request) -> RunMetricsResponse:
    run_store = _get_run_store(request)
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(404, f"Run not found: {run_id}")
    timings = run.stage_timings or []
    valid = [t for t in timings if t.get("duration_ms") is not None]
    slowest = max(valid, key=lambda t: t["duration_ms"], default=None)
    fastest = min(valid, key=lambda t: t["duration_ms"], default=None)
    return RunMetricsResponse(
        run_id=run.run_id,
        total_ms=run.total_ms,
        artifact_count=run.artifact_count,
        stage_timings=timings,
        slowest_stage=slowest["stage"] if slowest else None,
        fastest_stage=fastest["stage"] if fastest else None,
    )


@router.get("/{run_id}")
def get_run(run_id: str, request: Request) -> RunResponse:
    run_store = _get_run_store(request)
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(404, f"Run not found: {run_id}")
    job_store = _get_job_store_optional(request)
    input_text = _resolve_replay_input(run, job_store)
    replay_available = input_text is not None
    resp = _run_to_response(run, replay_available=replay_available)
    if run.job_id and job_store is not None:
        job = job_store.get(run.job_id)
        if job is not None:
            resp = resp.model_copy(update={"retry_count": job.retry_count})
    return resp


@router.post("/{run_id}/retry")
def retry_run(run_id: str, request: Request) -> RunActionResponse:
    return _replay_run(run_id, "retry", request)


@router.post("/{run_id}/rerun")
def rerun_run(run_id: str, request: Request) -> RunActionResponse:
    return _replay_run(run_id, "rerun", request)


def _replay_run(run_id: str, action_type: str, request: Request) -> RunActionResponse:
    from ..runs.models import RunRecord as _RunRecord
    from ..jobs.models import JobRecord as _JobRecord
    run_store = _get_run_store(request)
    job_store = _get_job_store_optional(request)
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(404, f"Run not found: {run_id}")
    if action_type == "retry" and run.status != RunStatus.FAILED:
        raise HTTPException(409, f"Only failed runs can be retried (status={run.status.value})")
    input_text = _resolve_replay_input(run, job_store)
    if input_text is None:
        raise HTTPException(422, "No input_text available to replay this run")

    job_id: Optional[str] = None
    if job_store is not None:
        # Create job first so we can link it to the new run
        job = _JobRecord.create(
            input_text=input_text,
            mode=run.mode,
            template_id=run.template_id,
            action_type=action_type,
            source_run_id=run_id,
        )
        job_id = job.job_id
        new_run = _RunRecord.create(
            source=RunSource.API_ASYNC,
            run_id=job.run_id,
            mode=run.mode,
            template_id=run.template_id,
            input_text=input_text,
            action_type=action_type,
            source_run_id=run_id,
            job_id=job_id,
        )
        run_store.create(new_run)
        job_store.submit(job)
    else:
        new_run = _RunRecord.create(
            source=run.source,
            mode=run.mode,
            template_id=run.template_id,
            input_text=input_text,
            action_type=action_type,
            source_run_id=run_id,
        )
        run_store.create(new_run)

    return RunActionResponse(
        run_id=new_run.run_id,
        source_run_id=run_id,
        action_type=action_type,
        job_id=job_id,
    )


@router.get("/{run_id}/artifacts")
def list_run_artifacts(run_id: str, request: Request) -> list[ArtifactMetadataResponse]:
    run_store = _get_run_store(request)
    artifact_store = _get_artifact_store(request)
    if run_store.get(run_id) is None:
        raise HTTPException(404, f"Run not found: {run_id}")
    artifacts = artifact_store.list_for_run(run_id)
    return [_artifact_to_response(a) for a in artifacts]


@router.get("/{run_id}/manifest")
def get_run_manifest(run_id: str, request: Request):
    run_store = _get_run_store(request)
    artifact_storage = _get_artifact_storage(request)
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(404, f"Run not found: {run_id}")
    if not run.manifest_path:
        raise HTTPException(404, "Manifest not available for this run")
    manifest_abs = artifact_storage.resolve(run.manifest_path)
    if not manifest_abs.exists():
        raise HTTPException(404, "Manifest file not found")
    return FileResponse(str(manifest_abs), media_type="application/json")
