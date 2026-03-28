"""Analytics data models — Phase 10D.1 / 10D.4.

Provides lightweight, immutable records for the governance analytics and
audit layer:

    FailureAttribution   — which artifact and stage caused a run to fail.
    ArtifactUsageEvent   — one resolved artifact's contribution to a run.
    GovernanceAuditEvent — immutable record of a governance-significant event.
    RunRecord            — top-level summary of a single pipeline run.

Most models are frozen dataclasses.  Each exposes ``to_dict()`` for JSON
serialisation and (where applicable) a ``from_dict()`` classmethod for
deserialisation.  No business logic lives here — capture and storage are
handled by separate modules in this package.

Phase 10D.4 adds two mutable-friendly records for per-run analytics:

    ArtifactUsageRecord   — richer per-artifact usage snapshot with scope
                            and governance signal fields.  Finalised at run
                            completion (success/failure flags mutated once).
    RunFailureAttribution — structured failure attribution with stage and
                            confidence level.  Only produced on failed runs.

Event type constants for :class:`GovernanceAuditEvent`::

    AUDIT_EVENT_DRAFT_OVERRIDE_USED      — runtime: draft artifact permitted
    AUDIT_EVENT_DEPRECATED_ARTIFACT_USED — runtime: deprecated artifact used
    AUDIT_EVENT_RUN_COMPLETED            — runtime: run finished successfully
    AUDIT_EVENT_RUN_FAILED               — runtime: run finished with error
    AUDIT_EVENT_VERSION_CREATED          — authoring: new version registered
    AUDIT_EVENT_VERSION_PROMOTED         — authoring: version → approved
    AUDIT_EVENT_VERSION_DEPRECATED       — authoring: version → deprecated
    AUDIT_EVENT_DEFAULT_VERSION_CHANGED  — authoring: family default pointer moved

Authoring events are defined here but not yet wired to a mutation API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Governance audit event type constants
# ---------------------------------------------------------------------------

#: Runtime event — a DRAFT artifact was permitted because allow_draft_artifacts
#: was True for this run.
AUDIT_EVENT_DRAFT_OVERRIDE_USED = "draft_override_used"

#: Runtime event — a DEPRECATED artifact was used.  A governance warning was
#: also emitted; this event carries the structured counterpart.
AUDIT_EVENT_DEPRECATED_ARTIFACT_USED = "deprecated_artifact_used"

#: Runtime event — a pipeline run completed without raising an exception.
AUDIT_EVENT_RUN_COMPLETED = "run_completed"

#: Runtime event — a pipeline run raised an exception before completion.
AUDIT_EVENT_RUN_FAILED = "run_failed"

# Authoring events — model defined here, emission wired when mutation API lands.
AUDIT_EVENT_VERSION_CREATED = "version_created"
AUDIT_EVENT_VERSION_PROMOTED = "version_promoted"
AUDIT_EVENT_VERSION_DEPRECATED = "version_deprecated"
AUDIT_EVENT_DEFAULT_VERSION_CHANGED = "default_version_changed"


# ---------------------------------------------------------------------------
# FailureAttribution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FailureAttribution:
    """Identifies which artifact and stage caused a pipeline run to fail.

    Attached to :class:`RunRecord` when a run raises a
    :class:`~pptgen.design_system.exceptions.DesignSystemError` or
    :class:`~pptgen.design_system.exceptions.GovernanceViolationError`
    during a resolution stage.

    Attributes:
        stage:         Pipeline resolution stage where the failure occurred.
                       One of ``"primitive"``, ``"layout"``, ``"theme"``,
                       ``"token_set"``, ``"asset"``.
        artifact_type: Canonical artifact category.  Matches *stage* for
                       direct failures.
        artifact_id:   Stable artifact identifier at the point of failure,
                       or ``None`` when the failure occurred before artifact
                       identity was established (e.g. registry miss).
        error_type:    Exception class name (e.g.
                       ``"GovernanceViolationError"``,
                       ``"DesignSystemError"``).
    """

    stage: str
    artifact_type: str
    artifact_id: str | None
    error_type: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "stage": self.stage,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "error_type": self.error_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailureAttribution:
        """Reconstruct from a plain dict (e.g. loaded from a JSONL line)."""
        return cls(
            stage=data["stage"],
            artifact_type=data["artifact_type"],
            artifact_id=data.get("artifact_id"),
            error_type=data["error_type"],
        )


# ---------------------------------------------------------------------------
# ArtifactUsageEvent
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtifactUsageEvent:
    """One resolved artifact's contribution to a single pipeline run.

    One event is created per distinct governed artifact in the run's
    dependency chain.  The collection of events for a run forms the
    per-run usage ledger and is the source of truth for usage aggregates.

    Attributes:
        run_id:           UUID of the pipeline run that produced this event.
        artifact_type:    Canonical artifact category — one of
                          ``"primitive"``, ``"layout"``, ``"theme"``,
                          ``"token_set"``, ``"asset"``.
        artifact_id:      Stable artifact identifier.
        version:          Version string at resolution time, or ``None``
                          when the artifact carries no governance block.
        lifecycle_status: Governance state at resolution time —
                          ``"approved"``, ``"draft"``, or
                          ``"deprecated"``.  ``None`` when no governance
                          block is present.
        was_default:      ``True`` when the resolved version matches the
                          artifact family's ``default_version`` pointer at
                          the time of the run.  ``False`` when the caller
                          pinned an explicit version or no family record
                          exists.
        run_succeeded:    ``True`` when the overall pipeline run completed
                          without error.
    """

    run_id: str
    artifact_type: str
    artifact_id: str
    version: str | None
    lifecycle_status: str | None
    was_default: bool
    run_succeeded: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "run_id": self.run_id,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "lifecycle_status": self.lifecycle_status,
            "was_default": self.was_default,
            "run_succeeded": self.run_succeeded,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactUsageEvent:
        """Reconstruct from a plain dict (e.g. loaded from a JSONL line)."""
        return cls(
            run_id=data["run_id"],
            artifact_type=data["artifact_type"],
            artifact_id=data["artifact_id"],
            version=data.get("version"),
            lifecycle_status=data.get("lifecycle_status"),
            was_default=bool(data["was_default"]),
            run_succeeded=bool(data["run_succeeded"]),
        )


# ---------------------------------------------------------------------------
# GovernanceAuditEvent
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GovernanceAuditEvent:
    """Immutable record of a governance-significant event.

    Audit events are append-only.  Once written to the audit log they are
    never modified.  The audit trail is the authoritative record of what
    happened and when.

    This dataclass is intentionally **not hashable** even though it is
    frozen, because the ``details`` field is a ``dict``.  Do not place
    instances in sets or use them as dict keys.

    Attributes:
        event_id:      UUID uniquely identifying this event.
        event_type:    Categorises the event.  See the
                       ``AUDIT_EVENT_*`` module constants.
        timestamp_utc: When the event occurred (UTC, timezone-aware or
                       naive — naive timestamps are treated as UTC).
        artifact_type: Affected artifact category, or ``None`` for
                       run-level events with no single artifact.
        artifact_id:   Affected artifact identifier, or ``None``.
        version:       Affected artifact version, or ``None``.
        run_id:        UUID of the pipeline run that triggered this event,
                       or ``None`` for authoring events that occur outside
                       a run.
        actor:         Identity of who or what triggered the event (e.g.
                       a CI job user env var), or ``None`` when
                       unavailable.
        details:       Event-type-specific payload.  Keys vary by
                       ``event_type``.  Callers must not mutate this dict
                       after construction.
    """

    event_id: str
    event_type: str
    timestamp_utc: datetime
    artifact_type: str | None = None
    artifact_id: str | None = None
    version: str | None = None
    run_id: str | None = None
    actor: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    # frozen=True with a dict field means __hash__ is generated but will
    # raise TypeError if called.  This is intentional — audit events are
    # records, not set members.
    def __hash__(self):  # type: ignore[override]
        raise TypeError(
            f"unhashable type: '{type(self).__name__}' "
            "(contains a mutable 'details' field)"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON output.

        ``timestamp_utc`` is rendered as an ISO 8601 string.
        ``details`` is shallow-copied to prevent the caller from mutating
        the serialised form.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "run_id": self.run_id,
            "actor": self.actor,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GovernanceAuditEvent:
        """Reconstruct from a plain dict (e.g. loaded from a JSONL line).

        ``timestamp_utc`` may be a pre-parsed :class:`~datetime.datetime`
        or an ISO 8601 string.
        """
        ts = data["timestamp_utc"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            timestamp_utc=ts,
            artifact_type=data.get("artifact_type"),
            artifact_id=data.get("artifact_id"),
            version=data.get("version"),
            run_id=data.get("run_id"),
            actor=data.get("actor"),
            details=dict(data.get("details", {})),
        )


# ---------------------------------------------------------------------------
# RunRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunRecord:
    """Top-level summary of a single pipeline run.

    One :class:`RunRecord` is created per invocation of
    :func:`~pptgen.pipeline.generation_pipeline.generate_presentation`.
    It is the primary correlation key (via ``run_id``) for all associated
    :class:`ArtifactUsageEvent` and :class:`GovernanceAuditEvent` records.

    Attributes:
        run_id:                UUID uniquely identifying this pipeline
                               invocation.
        timestamp_utc:         When the run started (UTC, timezone-aware
                               or naive).
        mode:                  Execution mode — ``"deterministic"`` or
                               ``"ai"``.
        playbook_id:           Playbook selected by the input router.
        template_id:           Template used for rendering, or ``None``.
        theme_id:              Design system theme applied, or ``None``.
        stage_reached:         Final completed stage —
                               ``"deck_planned"`` or ``"rendered"``.
        succeeded:             ``True`` when the run completed without
                               exception.
        failure_attribution:   Details of the failure, or ``None`` on
                               success.
        draft_override_active: ``True`` when ``allow_draft_artifacts=True``
                               was in effect for this run.
        dependency_count:      Number of distinct governed artifacts
                               resolved (``len(dependency_chain)``).
    """

    run_id: str
    timestamp_utc: datetime
    mode: str
    playbook_id: str
    template_id: str | None
    theme_id: str | None
    stage_reached: str
    succeeded: bool
    failure_attribution: FailureAttribution | None
    draft_override_active: bool
    dependency_count: int

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON output.

        ``timestamp_utc`` is rendered as ISO 8601.
        ``failure_attribution`` is serialised recursively, or ``None``.
        """
        return {
            "run_id": self.run_id,
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "mode": self.mode,
            "playbook_id": self.playbook_id,
            "template_id": self.template_id,
            "theme_id": self.theme_id,
            "stage_reached": self.stage_reached,
            "succeeded": self.succeeded,
            "failure_attribution": (
                self.failure_attribution.to_dict()
                if self.failure_attribution is not None
                else None
            ),
            "draft_override_active": self.draft_override_active,
            "dependency_count": self.dependency_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunRecord:
        """Reconstruct from a plain dict (e.g. loaded from a JSONL line).

        ``timestamp_utc`` may be a pre-parsed :class:`~datetime.datetime`
        or an ISO 8601 string.  ``failure_attribution`` is reconstructed
        recursively from its nested dict when present.
        """
        ts = data["timestamp_utc"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        fa_data = data.get("failure_attribution")
        return cls(
            run_id=data["run_id"],
            timestamp_utc=ts,
            mode=data["mode"],
            playbook_id=data["playbook_id"],
            template_id=data.get("template_id"),
            theme_id=data.get("theme_id"),
            stage_reached=data["stage_reached"],
            succeeded=bool(data["succeeded"]),
            failure_attribution=(
                FailureAttribution.from_dict(fa_data) if fa_data is not None else None
            ),
            draft_override_active=bool(data["draft_override_active"]),
            dependency_count=int(data["dependency_count"]),
        )


# ---------------------------------------------------------------------------
# ArtifactUsageRecord  (Phase 10D.4)
# ---------------------------------------------------------------------------


@dataclass
class ArtifactUsageRecord:
    """Richer per-artifact usage snapshot for a single pipeline run.

    One record is created per distinct (artifact_type, artifact_family,
    artifact_version, usage_scope) tuple encountered during resolution.
    Records are collected by :class:`~pptgen.analytics.GovernanceTelemetryCollector`
    and finalised at run completion via
    :meth:`~GovernanceTelemetryCollector.finalize_usage`.

    Unlike :class:`ArtifactUsageEvent` (the lightweight JSONL ledger record),
    this model carries governance signals captured *inline* during resolution —
    ``warning_emitted``, ``is_draft_override_usage`` — and scope context that
    identifies where in the pipeline the artifact was used.

    ``used_in_successful_run`` and ``used_in_failed_run`` are mutated exactly
    once at finalization.  All other fields are immutable after construction.

    Attributes:
        run_id:                 UUID of the pipeline run.  Backfilled by
                                :meth:`~GovernanceTelemetryCollector.finalize_usage`;
                                ``""`` before finalization.
        run_ts:                 Run start timestamp (UTC).
        artifact_type:          Canonical artifact category.
        artifact_family:        Stable artifact identifier (a.k.a. ``artifact_id``).
        artifact_version:       Resolved version string, or ``None`` when the
                                artifact carries no governance block.
        lifecycle_state:        Governance state at resolution time, or ``None``
                                when no governance block is present.
        resolution_source:      ``"explicit"`` when the artifact was named
                                directly in the deck/call; ``"default"`` when
                                resolved from a settings default.
        usage_scope:            ``"top_level"`` — primary artifact at deck root;
                                ``"dependency"`` — pulled in by another artifact
                                or by platform settings; ``"per_slide"`` — declared
                                on individual slides.
        warning_emitted:        ``True`` when a deprecation warning was added to
                                ``governance_warnings`` for this artifact.
        is_draft_override_usage: ``True`` when the artifact was DRAFT and used
                                 under ``allow_draft_artifacts=True``.
        used_in_successful_run: Set to ``True`` by ``finalize_usage(succeeded=True)``.
        used_in_failed_run:     Set to ``True`` by ``finalize_usage(succeeded=False)``.
    """

    run_id: str
    run_ts: datetime
    artifact_type: str
    artifact_family: str
    artifact_version: str | None
    lifecycle_state: str | None
    resolution_source: str  # "explicit" | "default"
    usage_scope: str        # "top_level" | "dependency" | "per_slide"
    warning_emitted: bool
    is_draft_override_usage: bool
    used_in_successful_run: bool = False
    used_in_failed_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for JSON output."""
        return {
            "run_id": self.run_id,
            "run_ts": self.run_ts.isoformat(),
            "artifact_type": self.artifact_type,
            "artifact_family": self.artifact_family,
            "artifact_version": self.artifact_version,
            "lifecycle_state": self.lifecycle_state,
            "resolution_source": self.resolution_source,
            "usage_scope": self.usage_scope,
            "warning_emitted": self.warning_emitted,
            "is_draft_override_usage": self.is_draft_override_usage,
            "used_in_successful_run": self.used_in_successful_run,
            "used_in_failed_run": self.used_in_failed_run,
        }


# ---------------------------------------------------------------------------
# RunFailureAttribution  (Phase 10D.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunFailureAttribution:
    """Structured failure attribution for a failed pipeline run.

    Provides a bounded, honest attribution of what stage a pipeline failure
    occurred at, and which artifact (if any) was the likely candidate.

    Attribution confidence:

    - ``"high"``   — failure occurred at a known governance or resolution
                     stage with a clear artifact candidate.
    - ``"medium"`` — failure occurred at render or export stage; artifact
                     context may be stale.
    - ``"low"``    — failure stage unknown or no artifact context available.

    Only produced when a :class:`~pptgen.pipeline.generation_pipeline.PipelineError`
    propagates out of :func:`~pptgen.pipeline.generation_pipeline.generate_presentation`.

    Attributes:
        run_id:                    UUID of the failed pipeline run.
        run_failed:                Always ``True`` for this record.
        failure_stage:             Where the failure occurred — ``"governance"``,
                                   ``"resolution"``, ``"render"``, ``"export"``,
                                   or ``"unknown"``.
        candidate_artifact_type:   Artifact category active at failure time,
                                   or ``None``.
        candidate_artifact_family: Artifact identifier active at failure time,
                                   or ``None``.
        candidate_artifact_version: Artifact version active at failure time,
                                    or ``None``.
        attribution_confidence:    ``"high"``, ``"medium"``, or ``"low"``.
        failure_message_summary:   First 200 characters of the exception message,
                                   or ``None``.
    """

    run_id: str
    run_failed: bool
    failure_stage: str   # "governance" | "resolution" | "render" | "export" | "unknown"
    candidate_artifact_type: str | None
    candidate_artifact_family: str | None
    candidate_artifact_version: str | None
    attribution_confidence: str  # "low" | "medium" | "high"
    failure_message_summary: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for JSON output."""
        return {
            "run_id": self.run_id,
            "run_failed": self.run_failed,
            "failure_stage": self.failure_stage,
            "candidate_artifact_type": self.candidate_artifact_type,
            "candidate_artifact_family": self.candidate_artifact_family,
            "candidate_artifact_version": self.candidate_artifact_version,
            "attribution_confidence": self.attribution_confidence,
            "failure_message_summary": self.failure_message_summary,
        }
