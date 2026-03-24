"""Run inspection endpoints — Stage 6C."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..runs.models import RunRecord
from .schemas import ArtifactMetadataResponse, RunResponse

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


def _get_artifact_storage(request: Request):
    s = getattr(request.app.state, "artifact_storage", None)
    if s is None:
        raise HTTPException(503, "Artifact storage not available")
    return s


def _run_to_response(run: RunRecord) -> RunResponse:
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


@router.get("/{run_id}")
def get_run(run_id: str, request: Request) -> RunResponse:
    run_store = _get_run_store(request)
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(404, f"Run not found: {run_id}")
    return _run_to_response(run)


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
