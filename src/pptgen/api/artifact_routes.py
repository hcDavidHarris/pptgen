"""Artifact inspection and download endpoints — Stage 6C."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..artifacts.models import ArtifactVisibility
from .run_routes import _artifact_to_response, _get_artifact_store, _get_artifact_storage
from .schemas import ArtifactMetadataResponse

router = APIRouter(prefix="/v1/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}/metadata")
def get_artifact_metadata(artifact_id: str, request: Request) -> ArtifactMetadataResponse:
    artifact_store = _get_artifact_store(request)
    artifact = artifact_store.get(artifact_id)
    if artifact is None:
        raise HTTPException(404, f"Artifact not found: {artifact_id}")
    return _artifact_to_response(artifact)


@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: str, request: Request) -> FileResponse:
    artifact_store = _get_artifact_store(request)
    artifact_storage = _get_artifact_storage(request)
    artifact = artifact_store.get(artifact_id)
    if artifact is None:
        raise HTTPException(404, f"Artifact not found: {artifact_id}")
    if artifact.visibility != ArtifactVisibility.DOWNLOADABLE:
        raise HTTPException(403, "Artifact is not available for download")
    abs_path = artifact_storage.resolve(artifact.relative_path)
    if not abs_path.exists():
        raise HTTPException(404, "Artifact file not found on disk")
    return FileResponse(
        str(abs_path),
        media_type=artifact.mime_type,
        filename=artifact.filename,
    )
