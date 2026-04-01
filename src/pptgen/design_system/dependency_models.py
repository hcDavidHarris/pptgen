"""Runtime dependency capture models — Phase 10C.

Provides a lightweight, immutable record of a governed artifact resolved
during a single pipeline run, and a shared helper for appending records
to a dependency chain without duplication.

Classes:
    ResolvedArtifactDependency — frozen snapshot of one resolved dependency.

Functions:
    record_dependency — append a dependency record to a chain, deduplicating
                        by (artifact_type, artifact_id, version).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResolvedArtifactDependency:
    """Immutable record of a single governed artifact resolved during a run.

    One instance is created for every distinct governed artifact encountered
    during pipeline resolution.  The collection of all instances for a run is
    stored in :attr:`~pptgen.pipeline.generation_pipeline.PipelineResult.dependency_chain`.

    Attributes:
        artifact_type:    Canonical artifact category — one of ``"primitive"``,
                          ``"layout"``, ``"theme"``, ``"token_set"``, ``"asset"``.
        artifact_id:      Stable artifact identifier (e.g. ``"bullet_slide"``,
                          ``"executive"``, ``"icon.check"``).
        version:          Version string at resolution time (e.g. ``"1.0.0"``),
                          or ``None`` when the artifact has no governance block.
        lifecycle_status: Governance lifecycle state at resolution time —
                          ``"approved"``, ``"draft"``, or ``"deprecated"``.
                          ``None`` when the artifact carries no governance block.
        source:           Pipeline stage that produced this record.  In Phase
                          10C this matches ``artifact_type`` for all five types.
                          Kept distinct to support future cases where a
                          transitive dependency is captured inside a different
                          resolution stage (e.g. a layout captured while
                          processing a primitive).
    """

    artifact_type: str
    artifact_id: str
    version: str | None
    lifecycle_status: str | None
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON snapshot export."""
        return {
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "lifecycle_status": self.lifecycle_status,
            "source": self.source,
        }


def record_dependency(
    chain: list[ResolvedArtifactDependency],
    artifact_type: str,
    artifact_id: str,
    version: str | None,
    lifecycle_status: str | None,
    source: str,
) -> None:
    """Append a dependency record to *chain*, skipping exact duplicates.

    Deduplication key is ``(artifact_type, artifact_id, version)``.  A linear
    scan is used because the chain length is bounded by the number of distinct
    governed artifact types resolved per run (typically ≤ 10 entries, including
    all assets).

    This function is intentionally placed in this module — not in
    ``generation_pipeline`` — so that ``asset_resolver`` can import it without
    creating a circular dependency.

    Args:
        chain:            Mutable list of :class:`ResolvedArtifactDependency`
                          instances accumulated during the current run.
        artifact_type:    Canonical artifact type string.
        artifact_id:      Stable artifact identifier.
        version:          Resolved version string, or ``None``.
        lifecycle_status: Governance status string at resolution time, or
                          ``None`` when no governance block is present.
        source:           Pipeline stage name that triggered this capture.
    """
    key = (artifact_type, artifact_id, version)
    for existing in chain:
        if (existing.artifact_type, existing.artifact_id, existing.version) == key:
            return  # already recorded — skip
    chain.append(
        ResolvedArtifactDependency(
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            version=version,
            lifecycle_status=lifecycle_status,
            source=source,
        )
    )
