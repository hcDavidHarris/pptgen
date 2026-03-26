"""Template resolution logic — Phase 8 Stage 1 + Stage 3.

Implements deterministic, replay-safe template version resolution for three
execution modes:

* **new_run** — Resolve the governance default version, or an exact pinned
  version if the caller specifies one.  Lifecycle is enforced: non-approved
  templates are rejected for new runs.
* **retry** — Pin the exact version recorded in the original run (no resolution).
  Lifecycle and deprecation are NOT checked so existing runs remain reproducible.
* **rerun** — Same as retry; version is inherited from the source run.

The optional *governance* parameter enables Stage 3 governance enforcement.
When ``None`` the Stage 1 behaviour is preserved for backward compatibility.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from .models import TemplateVersion
from .registry import VersionedTemplateRegistry, _parse_semver

if TYPE_CHECKING:
    from .governance import GovernanceStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default version resolution (manifest-only, no governance)
# ---------------------------------------------------------------------------

def resolve_template_default_version(
    registry: VersionedTemplateRegistry,
    template_id: str,
) -> TemplateVersion | None:
    """Return the highest-versioned entry for an approved (or under-review) template.

    Uses manifest lifecycle only; ignores governance overrides.
    Returns ``None`` when the template is not found, deprecated, or has no versions.
    """
    template = registry.get_template(template_id)
    if template is None:
        return None
    if template.lifecycle_status not in ("approved", "review"):
        return None
    versions = sorted(
        template.versions,
        key=lambda v: _parse_semver(v.version),
        reverse=True,
    )
    return versions[0] if versions else None


# ---------------------------------------------------------------------------
# New-run resolution
# ---------------------------------------------------------------------------

def resolve_template_for_run(
    registry: VersionedTemplateRegistry,
    template_id: str,
    version: Optional[str] = None,
    run_id: Optional[str] = None,
    governance: Optional["GovernanceStore"] = None,
) -> TemplateVersion | None:
    """Resolve a template version for a new run.

    If *version* is supplied the exact match is returned.
    If *version* is ``None`` the governance/manifest default version is used.

    When *governance* is provided:
    - The effective lifecycle is enforced (non-approved → ``None``).
    - Deprecated versions cannot be used for new runs.
    - The governance-pinned default version is preferred over semver ordering.

    Returns ``None`` when the template or version is not found, or when
    lifecycle/deprecation rules block the run.

    Emits a ``template_resolved`` structured log event when a version is found.
    """
    if governance is not None:
        from .governance import (
            get_effective_lifecycle,
            get_effective_default_version,
            is_new_run_allowed,
        )
        lifecycle = get_effective_lifecycle(registry, governance, template_id)
        if not is_new_run_allowed(lifecycle):
            logger.warning(
                "template_lifecycle_block",
                extra={
                    "event": "template_lifecycle_block",
                    "template_id": template_id,
                    "lifecycle_status": lifecycle,
                    "run_id": run_id,
                },
            )
            return None

        if version:
            result = registry.get_template_version(template_id, version)
            if result and governance.is_deprecated(template_id, version):
                logger.warning(
                    "template_deprecated_block",
                    extra={
                        "event": "template_deprecated_block",
                        "template_id": template_id,
                        "template_version": version,
                        "run_id": run_id,
                    },
                )
                return None
            resolution_mode = "new_run_pinned"
        else:
            result = get_effective_default_version(registry, governance, template_id)
            resolution_mode = "new_run_default"
    else:
        # Governance-free path (Stage 1 compatibility)
        if version:
            result = registry.get_template_version(template_id, version)
            resolution_mode = "new_run_pinned"
        else:
            result = resolve_template_default_version(registry, template_id)
            resolution_mode = "new_run_default"

    if result is not None:
        _log_resolution(run_id, template_id, result, resolution_mode)
    return result


# ---------------------------------------------------------------------------
# Replay resolution (retry / rerun)
# ---------------------------------------------------------------------------

def resolve_template_for_replay(
    registry: VersionedTemplateRegistry,
    template_id: str,
    pinned_version: str,
    run_id: Optional[str] = None,
    governance: Optional["GovernanceStore"] = None,
) -> TemplateVersion | None:
    """Resolve a template version for a retry or rerun.

    The *pinned_version* recorded on the original run is used exactly — no
    default resolution is performed.

    Governance lifecycle and deprecation are intentionally NOT enforced here:
    deprecated templates and deprecated versions must remain replayable to
    preserve the immutability guarantee of existing runs.

    Returns ``None`` if the pinned version is no longer present in the registry.

    Emits a ``template_resolved`` structured log event when a version is found.
    """
    result = registry.get_template_version(template_id, pinned_version)
    if result is not None:
        _log_resolution(run_id, template_id, result, "replay")
    return result


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _log_resolution(
    run_id: Optional[str],
    template_id: str,
    version: TemplateVersion,
    resolution_mode: str,
) -> None:
    logger.info(
        "template_resolved",
        extra={
            "event": "template_resolved",
            "run_id": run_id,
            "template_id": template_id,
            "template_version": version.version,
            "template_revision_hash": version.template_revision_hash,
            "resolution_mode": resolution_mode,
        },
    )
