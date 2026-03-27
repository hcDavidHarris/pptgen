"""Governance data models — Phase 10A.

Defines the core governance model across all artifact types:
primitives, layouts, themes, tokens, and assets.

This module is strictly data — no business logic, no enforcement rules,
no lifecycle transitions.  Runtime enforcement is Phase 10B.

Classes:
    LifecycleStatus          — allowed lifecycle states for any artifact version.
    GovernedArtifactVersion  — versioned snapshot of an artifact with its
                               governance metadata.
    GovernedArtifactFamily   — family-level pointer that carries the
                               default version designation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LifecycleStatus(str, Enum):
    """Allowed lifecycle states for a governed artifact version.

    Inherits from ``str`` so values serialise transparently in JSON/YAML and
    can be compared directly to string literals without ``.value``.
    """

    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class GovernedArtifactVersion:
    """Versioned snapshot of any design-system artifact with governance metadata.

    Attributes:
        artifact_id:        Stable identifier for the artifact
                            (e.g. ``"bullet_slide"``, ``"executive"``).
        artifact_type:      One of ``"primitive"``, ``"layout"``, ``"theme"``,
                            ``"token"``, ``"asset"``.
        version:            Semantic version string (e.g. ``"1.0.0"``).
        lifecycle_status:   Current lifecycle state.  Defaults to ``APPROVED``
                            when the governance block is absent from the YAML.
        created_at:         UTC timestamp of initial creation.
        created_by:         Identity of the author who created this version.
        promoted_at:        UTC timestamp when status was set to ``APPROVED``.
        promoted_by:        Identity who performed the promotion.
        deprecated_at:      UTC timestamp when status was set to ``DEPRECATED``.
        deprecated_by:      Identity who performed the deprecation.
        deprecation_reason: Human-readable explanation of why the version was
                            deprecated.
    """

    artifact_id: str
    artifact_type: str
    version: str
    lifecycle_status: LifecycleStatus
    created_at: datetime | None = None
    created_by: str | None = None
    promoted_at: datetime | None = None
    promoted_by: str | None = None
    deprecated_at: datetime | None = None
    deprecated_by: str | None = None
    deprecation_reason: str | None = None


@dataclass(frozen=True)
class GovernedArtifactFamily:
    """Family-level descriptor for an artifact across all its versions.

    The *family* groups all versions of the same ``artifact_id`` and
    designates which version callers should use when no explicit version is
    requested.

    Attributes:
        artifact_id:      Stable identifier shared by all versions in this
                          family.
        artifact_type:    Artifact category (same values as
                          :class:`GovernedArtifactVersion`).
        default_version:  Version string that ``resolve_artifact_version()``
                          returns when no explicit version is given.  ``None``
                          when no default has been declared.
    """

    artifact_id: str
    artifact_type: str
    default_version: str | None
