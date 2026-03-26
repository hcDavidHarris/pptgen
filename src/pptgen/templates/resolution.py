"""Template resolution logic — Phase 8 Stage 1.

Implements deterministic, replay-safe template version resolution for three
execution modes:

* **new_run** — Resolve the latest approved version, or an exact pinned version
  if the caller specifies one.
* **retry** — Pin the exact version recorded in the original run (no resolution).
* **rerun** — Same as retry; version is inherited from the source run.

Resolution events are emitted as structured log entries so operators can audit
which template version was selected for each run.
"""
from __future__ import annotations

import logging
from typing import Optional

from .models import TemplateVersion
from .registry import VersionedTemplateRegistry, _parse_semver

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default version resolution
# ---------------------------------------------------------------------------

def resolve_template_default_version(
    registry: VersionedTemplateRegistry,
    template_id: str,
) -> TemplateVersion | None:
    """Return the highest-versioned entry for an approved (or under-review) template.

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
) -> TemplateVersion | None:
    """Resolve a template version for a new run.

    If *version* is supplied the exact match is returned.
    If *version* is ``None`` the default approved version is used.
    Returns ``None`` when the template or version is not found.

    Emits a ``template_resolved`` structured log event when a version is found.
    """
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
) -> TemplateVersion | None:
    """Resolve a template version for a retry or rerun.

    The *pinned_version* recorded on the original run is used exactly — no
    default resolution is performed.  Returns ``None`` if the pinned version is
    no longer present in the registry (operator should investigate).

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
