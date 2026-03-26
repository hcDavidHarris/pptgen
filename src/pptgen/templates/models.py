"""Template domain models for Phase 8 Stage 1."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TemplateVersion:
    """Immutable snapshot of a template at a specific semantic version.

    ``template_revision_hash`` is derived from template_id + version + manifest
    entry fields so that replay correctness can be verified even after config drift.
    """

    version_id: str              # deterministic UUID5 from (template_id, version)
    template_id: str
    version: str                 # semantic version string e.g. "1.0.0"
    template_revision_hash: str  # SHA-256[:16] of manifest entry content

    template_path: Optional[str] = None          # relative path to .pptx file
    playbook_path: Optional[str] = None          # path to playbook YAML (future)
    input_contract_version: Optional[str] = None
    ai_mode: str = "optional"                    # "optional" | "required" | "disabled"

    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )


@dataclass
class Template:
    """Stable identity of a registered template.

    A Template may have multiple :class:`TemplateVersion` entries.  Only one
    version is active for new runs at a time (the default approved version), but
    existing runs pin their version at creation for replay safety.
    """

    template_id: str
    template_key: str      # canonical key — same as template_id in Stage 1
    name: str

    description: Optional[str] = None
    owner: Optional[str] = None
    lifecycle_status: str = "draft"   # "draft" | "review" | "approved" | "deprecated"

    versions: list[TemplateVersion] = field(default_factory=list)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
