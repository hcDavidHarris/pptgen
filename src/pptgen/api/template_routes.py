"""Template registry API endpoints — Phase 8 Stage 1 + Stage 2 + Stage 3.

Exposes read-only and governance endpoints for the versioned template registry:

    GET  /v1/templates/{template_id}
    GET  /v1/templates/{template_id}/versions
    GET  /v1/templates/{template_id}/runs
    GET  /v1/templates/{template_id}/governance
    GET  /v1/templates/{template_id}/governance/audit
    POST /v1/templates/{template_id}/versions/{version}/promote
    POST /v1/templates/{template_id}/versions/{version}/deprecate
    POST /v1/templates/{template_id}/lifecycle

The pre-existing ``GET /v1/templates`` endpoint (legacy list of IDs) is
preserved in ``routes.py`` for backward compatibility.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from .schemas import (
    DeprecateVersionRequest,
    GovernanceActionResponse,
    GovernanceAuditEvent,
    GovernanceStateResponse,
    LifecycleChangeRequest,
    PromoteVersionRequest,
    TemplateDetailResponse,
    TemplateRunItem,
    TemplateRunsResponse,
    TemplateUsageSummaryResponse,
    TemplateVersionResponse,
    TemplateVersionUsageItem,
    TemplateVersionUsageResponse,
    TemplateUsageTrendItem,
    TemplateUsageTrendResponse,
    TemplateVersionWithGovernance,
)

router = APIRouter(prefix="/v1/templates", tags=["templates"])


# ---------------------------------------------------------------------------
# Store accessors
# ---------------------------------------------------------------------------

def _get_registry(request: Request):
    reg = getattr(request.app.state, "template_registry", None)
    if reg is None:
        raise HTTPException(503, "Template registry not available")
    return reg


def _get_governance(request: Request):
    gov = getattr(request.app.state, "governance_store", None)
    if gov is None:
        raise HTTPException(503, "Governance store not available")
    return gov


def _get_governance_optional(request: Request):
    return getattr(request.app.state, "governance_store", None)


def _get_run_store(request: Request):
    store = getattr(request.app.state, "run_store", None)
    if store is None:
        raise HTTPException(503, "Run store not available")
    return store


# ---------------------------------------------------------------------------
# GET /v1/templates/{template_id}
# ---------------------------------------------------------------------------

@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(template_id: str, request: Request) -> TemplateDetailResponse:
    """Return metadata and version list for a registered template."""
    reg = _get_registry(request)
    template = reg.get_template(template_id)
    if template is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    gov = _get_governance_optional(request)

    # Apply governance lifecycle override if available
    from ..templates.governance import get_effective_lifecycle
    lifecycle = (
        get_effective_lifecycle(reg, gov, template_id)
        if gov is not None
        else template.lifecycle_status
    )
    versions = reg.get_template_versions(template_id)
    return TemplateDetailResponse(
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        owner=template.owner,
        lifecycle_status=lifecycle,
        versions=[v.version for v in versions],
    )


# ---------------------------------------------------------------------------
# GET /v1/templates/{template_id}/versions
# ---------------------------------------------------------------------------

@router.get("/{template_id}/versions", response_model=list[TemplateVersionWithGovernance])
def list_template_versions(
    template_id: str, request: Request
) -> list[TemplateVersionWithGovernance]:
    """Return all versions with full metadata including governance state."""
    reg = _get_registry(request)
    template = reg.get_template(template_id)
    if template is None:
        raise HTTPException(404, f"Template not found: {template_id}")

    gov = _get_governance_optional(request)
    default_version = gov.get_default_version(template_id) if gov else None

    # If no explicit default, fall back to highest semver (same logic as resolution)
    if default_version is None and gov is not None:
        from ..templates.governance import get_effective_default_version
        dv = get_effective_default_version(reg, gov, template_id)
        if dv:
            default_version = dv.version

    result = []
    for v in reg.get_template_versions(template_id):
        dep = gov.get_deprecation(template_id, v.version) if gov else None
        promo_ts = gov.get_promotion_timestamp(template_id, v.version) if gov else None
        result.append(
            TemplateVersionWithGovernance(
                version=v.version,
                template_revision_hash=v.template_revision_hash,
                template_path=v.template_path,
                playbook_path=v.playbook_path,
                input_contract_version=v.input_contract_version,
                ai_mode=v.ai_mode,
                is_default=(v.version == default_version),
                deprecated_at=dep["deprecated_at"].isoformat() if dep else None,
                deprecation_reason=dep["reason"] if dep else None,
                promotion_timestamp=promo_ts.isoformat() if promo_ts else None,
            )
        )
    return result


# ---------------------------------------------------------------------------
# GET /v1/templates/{template_id}/governance
# ---------------------------------------------------------------------------

@router.get("/{template_id}/governance", response_model=GovernanceStateResponse)
def get_governance_state(template_id: str, request: Request) -> GovernanceStateResponse:
    """Return effective governance state for a template."""
    reg = _get_registry(request)
    if reg.get_template(template_id) is None:
        raise HTTPException(404, f"Template not found: {template_id}")

    gov = _get_governance(request)
    from ..templates.governance import get_effective_lifecycle, get_effective_default_version
    lifecycle = get_effective_lifecycle(reg, gov, template_id)
    dv = get_effective_default_version(reg, gov, template_id)
    deprecated = gov.get_deprecated_versions(template_id)
    return GovernanceStateResponse(
        template_id=template_id,
        lifecycle_status=lifecycle,
        default_version=dv.version if dv else None,
        deprecated_versions=deprecated,
    )


# ---------------------------------------------------------------------------
# GET /v1/templates/{template_id}/governance/audit
# ---------------------------------------------------------------------------

@router.get("/{template_id}/governance/audit", response_model=list[GovernanceAuditEvent])
def get_governance_audit(
    template_id: str,
    request: Request,
    limit: int = 100,
) -> list[GovernanceAuditEvent]:
    """Return the governance audit trail for a template, newest first."""
    reg = _get_registry(request)
    if reg.get_template(template_id) is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    gov = _get_governance(request)
    events = gov.list_audit_events(template_id=template_id, limit=limit)
    return [
        GovernanceAuditEvent(
            event_type=e["event_type"],
            template_id=e["template_id"],
            template_version=e["template_version"],
            actor=e["actor"],
            reason=e["reason"],
            timestamp=e["timestamp"],
            metadata=e["metadata"],
        )
        for e in events
    ]


# ---------------------------------------------------------------------------
# POST /v1/templates/{template_id}/versions/{version}/promote
# ---------------------------------------------------------------------------

@router.post(
    "/{template_id}/versions/{version}/promote",
    response_model=GovernanceActionResponse,
)
def promote_version(
    template_id: str,
    version: str,
    body: PromoteVersionRequest,
    request: Request,
) -> GovernanceActionResponse:
    """Promote *version* to be the default production version for this template."""
    reg = _get_registry(request)
    gov = _get_governance(request)

    from ..templates.governance import validate_version_promotable
    try:
        validate_version_promotable(reg, gov, template_id, version)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    previous = gov.set_default_version(
        template_id, version, actor=body.actor, reason=body.reason
    )

    # Emit structured log + audit event
    _emit_governance_log(
        "template_version_promoted",
        template_id=template_id,
        version=version,
        previous_default=previous,
        actor=body.actor,
        reason=body.reason,
    )
    gov.add_audit_event(
        "template_version_promoted",
        template_id=template_id,
        template_version=version,
        actor=body.actor,
        reason=body.reason,
        previous_default=previous,
    )

    return GovernanceActionResponse(
        template_id=template_id,
        version=version,
        action="promoted",
        accepted=True,
        message=f"Version {version} is now the default for {template_id}.",
        previous_default=previous,
    )


# ---------------------------------------------------------------------------
# POST /v1/templates/{template_id}/versions/{version}/deprecate
# ---------------------------------------------------------------------------

@router.post(
    "/{template_id}/versions/{version}/deprecate",
    response_model=GovernanceActionResponse,
)
def deprecate_version(
    template_id: str,
    version: str,
    body: DeprecateVersionRequest,
    request: Request,
) -> GovernanceActionResponse:
    """Deprecate *version* so it is no longer used for new runs."""
    reg = _get_registry(request)
    gov = _get_governance(request)

    from ..templates.governance import validate_version_deprecatable
    try:
        validate_version_deprecatable(reg, gov, template_id, version)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    gov.deprecate_version(
        template_id, version, reason=body.reason, actor=body.actor
    )

    # If this was the default version, clear the explicit default so resolution falls back
    if gov.get_default_version(template_id) == version:
        gov._conn.execute(
            "UPDATE template_version_governance SET is_default = 0 WHERE template_id = ? AND version = ?",
            (template_id, version),
        )
        gov._conn.commit()

    _emit_governance_log(
        "template_version_deprecated",
        template_id=template_id,
        version=version,
        reason=body.reason,
        actor=body.actor,
    )
    gov.add_audit_event(
        "template_version_deprecated",
        template_id=template_id,
        template_version=version,
        actor=body.actor,
        reason=body.reason,
    )

    return GovernanceActionResponse(
        template_id=template_id,
        version=version,
        action="deprecated",
        accepted=True,
        message=f"Version {version} of {template_id} is now deprecated.",
    )


# ---------------------------------------------------------------------------
# POST /v1/templates/{template_id}/lifecycle
# ---------------------------------------------------------------------------

@router.post("/{template_id}/lifecycle", response_model=GovernanceActionResponse)
def change_lifecycle(
    template_id: str,
    body: LifecycleChangeRequest,
    request: Request,
) -> GovernanceActionResponse:
    """Change the lifecycle status of *template_id* at runtime."""
    reg = _get_registry(request)
    if reg.get_template(template_id) is None:
        raise HTTPException(404, f"Template not found: {template_id}")

    gov = _get_governance(request)
    from ..templates.governance import (
        get_effective_lifecycle,
        validate_lifecycle_transition,
    )
    current = get_effective_lifecycle(reg, gov, template_id)
    try:
        validate_lifecycle_transition(current, body.lifecycle_status)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    gov.set_lifecycle(
        template_id,
        body.lifecycle_status,
        actor=body.actor,
        reason=body.reason,
    )

    _emit_governance_log(
        "template_lifecycle_changed",
        template_id=template_id,
        previous_lifecycle=current,
        new_lifecycle=body.lifecycle_status,
        actor=body.actor,
        reason=body.reason,
    )
    gov.add_audit_event(
        "template_lifecycle_changed",
        template_id=template_id,
        actor=body.actor,
        reason=body.reason,
        previous_lifecycle=current,
        new_lifecycle=body.lifecycle_status,
    )

    return GovernanceActionResponse(
        template_id=template_id,
        action="lifecycle_changed",
        accepted=True,
        message=(
            f"Lifecycle of {template_id} changed "
            f"from '{current}' to '{body.lifecycle_status}'."
        ),
    )


# ---------------------------------------------------------------------------
# GET /v1/templates/{template_id}/runs  (from Stage 2)
# ---------------------------------------------------------------------------

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
    """Return runs that used this template, newest first."""
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


# ---------------------------------------------------------------------------
# GET /v1/templates/{template_id}/analytics/summary
# GET /v1/templates/{template_id}/analytics/versions
# GET /v1/templates/{template_id}/analytics/trend
# ---------------------------------------------------------------------------

@router.get("/{template_id}/analytics/summary", response_model=TemplateUsageSummaryResponse)
def get_template_analytics_summary(
    template_id: str,
    request: Request,
    days: int = 30,
) -> TemplateUsageSummaryResponse:
    """Return aggregate run metrics for *template_id* over the last *days* days."""
    reg = _get_registry(request)
    if reg.get_template(template_id) is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    run_store = _get_run_store(request)
    summary = run_store.get_template_usage_summary(template_id, days=days)
    return TemplateUsageSummaryResponse(**summary)


@router.get("/{template_id}/analytics/versions", response_model=TemplateVersionUsageResponse)
def get_template_analytics_versions(
    template_id: str,
    request: Request,
    days: int = 30,
) -> TemplateVersionUsageResponse:
    """Return per-version run metrics for *template_id* over the last *days* days."""
    reg = _get_registry(request)
    if reg.get_template(template_id) is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    run_store = _get_run_store(request)
    rows = run_store.get_template_version_usage(template_id, days=days)
    return TemplateVersionUsageResponse(
        template_id=template_id,
        date_window_days=days,
        versions=[TemplateVersionUsageItem(**r) for r in rows],
    )


@router.get("/{template_id}/analytics/trend", response_model=TemplateUsageTrendResponse)
def get_template_analytics_trend(
    template_id: str,
    request: Request,
    days: int = 30,
) -> TemplateUsageTrendResponse:
    """Return daily adoption trend per version for *template_id* over the last *days* days."""
    reg = _get_registry(request)
    if reg.get_template(template_id) is None:
        raise HTTPException(404, f"Template not found: {template_id}")
    run_store = _get_run_store(request)
    rows = run_store.get_template_usage_trend(template_id, days=days)
    return TemplateUsageTrendResponse(
        template_id=template_id,
        date_window_days=days,
        trend=[TemplateUsageTrendItem(**r) for r in rows],
    )


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

import logging as _logging
_logger = _logging.getLogger(__name__)


def _emit_governance_log(event_type: str, **kwargs) -> None:
    _logger.info(event_type, extra={"event": event_type, **kwargs})
