"""Template registry API endpoints — Phase 8 Stage 1 + Stage 2.

Exposes read-only access to the versioned template registry:

    GET /v1/templates/{template_id}
    GET /v1/templates/{template_id}/versions
    GET /v1/templates/{template_id}/runs

The pre-existing ``GET /v1/templates`` endpoint (legacy list of IDs) is
preserved in ``routes.py`` for backward compatibility.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from .schemas import TemplateDetailResponse, TemplateRunItem, TemplateRunsResponse, TemplateVersionResponse

router = APIRouter(prefix="/v1/templates", tags=["templates"])


def _get_registry(request: Request):
    reg = getattr(request.app.state, "template_registry", None)
    if reg is None:
        raise HTTPException(503, "Template registry not available")
    return reg


def _get_run_store(request: Request):
    store = getattr(request.app.state, "run_store", None)
    if store is None:
        raise HTTPException(503, "Run store not available")
    return store


@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(template_id: str, request: Request) -> TemplateDetailResponse:
    """Return metadata and version list for a registered template."""
    reg = _get_registry(request)
    template = reg.get_template(template_id)
    if template is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    versions = reg.get_template_versions(template_id)
    return TemplateDetailResponse(
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        owner=template.owner,
        lifecycle_status=template.lifecycle_status,
        versions=[v.version for v in versions],
    )


@router.get("/{template_id}/versions", response_model=list[TemplateVersionResponse])
def list_template_versions(
    template_id: str, request: Request
) -> list[TemplateVersionResponse]:
    """Return all versions of a template with full metadata."""
    reg = _get_registry(request)
    template = reg.get_template(template_id)
    if template is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    return [
        TemplateVersionResponse(
            version=v.version,
            template_revision_hash=v.template_revision_hash,
            template_path=v.template_path,
            playbook_path=v.playbook_path,
            input_contract_version=v.input_contract_version,
            ai_mode=v.ai_mode,
        )
        for v in reg.get_template_versions(template_id)
    ]


_30_DAYS_ISO = None   # computed lazily per-request to avoid stale module-level datetime


@router.get("/{template_id}/runs", response_model=TemplateRunsResponse)
def get_template_runs(
    template_id: str,
    request: Request,
    template_version: Optional[str] = None,
    status: Optional[str] = None,
    days: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> TemplateRunsResponse:
    """Return runs that used this template, newest first.

    Optional filters:
    - ``template_version``: exact version string (e.g. ``"1.0.0"``)
    - ``status``: run status (``succeeded`` / ``failed`` / …)
    - ``days``: restrict to runs started within the last N days (default: all time)
    """
    reg = _get_registry(request)
    if reg.get_template(template_id) is None:
        raise HTTPException(404, f"Template not found: {template_id}")

    run_store = _get_run_store(request)

    since_iso: Optional[str] = None
    if days is not None and days > 0:
        since_iso = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()

    runs = run_store.list_runs_by_template(
        template_id=template_id,
        template_version=template_version,
        limit=limit,
        offset=offset,
        status=status,
        since_iso=since_iso,
    )
    items = [
        TemplateRunItem(
            run_id=r.run_id,
            status=r.status.value,
            template_version=r.template_version,
            template_revision_hash=r.template_revision_hash,
            started_at=r.started_at.isoformat(),
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            total_ms=r.total_ms,
            artifact_count=r.artifact_count,
            error_category=r.error_category,
            mode=r.mode,
            playbook_id=r.playbook_id,
        )
        for r in runs
    ]
    return TemplateRunsResponse(
        template_id=template_id,
        runs=items,
        total=len(items),
        limit=limit,
        offset=offset,
    )
