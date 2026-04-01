"""Governance telemetry collector — Phase 10D.5 / 10D.4.

Run-scoped accumulator for governance audit events and artifact usage records.
One instance is created at the top of ``generate_presentation()`` and passed
as ``telemetry=`` to all resolution helpers.  This prevents raw-list threading
and gives the event accumulation interface a stable place to grow.

Event categories
----------------
Runtime events — emitted during pipeline execution by the collector:

    AUDIT_EVENT_DRAFT_OVERRIDE_USED
        A DRAFT artifact was resolved with ``allow_draft_artifacts=True``.

    AUDIT_EVENT_DEPRECATED_ARTIFACT_USED
        A DEPRECATED artifact was resolved; a human-readable warning is also
        appended to ``governance_warnings``.

    AUDIT_EVENT_RUN_COMPLETED / AUDIT_EVENT_RUN_FAILED
        Top-level run outcomes — emitted at the RunRecord layer, not here.

Control-plane events — authoring / governance mutations (Phase 10D.6 stubs):

    AUDIT_EVENT_VERSION_CREATED
    AUDIT_EVENT_VERSION_PROMOTED
    AUDIT_EVENT_VERSION_DEPRECATED
    AUDIT_EVENT_DEFAULT_VERSION_CHANGED

Control-plane events are not emitted by the collector; they will be produced
by ``emit_authoring_event()`` (Phase 10D.6) and written to the same
``audit_events.jsonl`` file.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .analytics_models import (
    AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
    AUDIT_EVENT_DRAFT_OVERRIDE_USED,
    ArtifactUsageRecord,
    GovernanceAuditEvent,
    RunFailureAttribution,
)

# Failure stage → (stage_name, confidence) mapping for known exception types.
# Checked by get_failure_attribution() via class-name string to avoid circular
# imports from design_system.exceptions.
_GOVERNANCE_VIOLATION_NAMES = frozenset({"GovernanceViolationError"})
_DESIGN_SYSTEM_ERROR_NAMES = frozenset({
    "DesignSystemError",
    "ArtifactNotFoundError",
    "ArtifactVersionNotFoundError",
    "InvalidArtifactError",
})


class GovernanceTelemetryCollector:
    """Run-scoped accumulator for governance telemetry.

    Instantiated once per pipeline run.  Passed to every resolution helper
    as ``telemetry=`` so that the per-helper signature stays stable as
    Phase 10D grows.

    Usage::

        telemetry = GovernanceTelemetryCollector(run_ts=datetime.now(timezone.utc))
        telemetry.mark_stage("resolution")
        # helpers append events/usage through record_* methods ...
        events = telemetry.get_audit_events()       # snapshot copy
        records = telemetry.get_usage_records()     # snapshot copy (before finalize)
        telemetry.finalize_usage(succeeded=True, run_id="<uuid>")

    All ``record_*`` methods create and append a :class:`GovernanceAuditEvent`
    with ``run_id=None``.  The caller is responsible for backfilling ``run_id``
    (via :func:`~pptgen.pipeline.generation_pipeline._backfill_run_id`) before
    attaching events to :class:`~pptgen.pipeline.generation_pipeline.PipelineResult`.
    """

    def __init__(self, run_ts: datetime | None = None) -> None:
        self._audit_events: list[GovernanceAuditEvent] = []
        self._run_ts: datetime = run_ts if run_ts is not None else datetime.now(timezone.utc)
        # Usage records keyed by (artifact_type, artifact_family, artifact_version, usage_scope).
        # Dict preserves insertion order (Python 3.7+); values are merged on collision.
        self._usage_records: dict[tuple, ArtifactUsageRecord] = {}
        self._current_stage: str = "resolution"
        self._failure_context: dict | None = None
        # Finalization is idempotent: subsequent calls to finalize_usage() are no-ops.
        self._finalized: bool = False

    # ------------------------------------------------------------------
    # Emission helpers
    # ------------------------------------------------------------------

    def record_audit_event(self, event: GovernanceAuditEvent) -> None:
        """Append a pre-built :class:`~.analytics_models.GovernanceAuditEvent`.

        Use when the caller has already constructed the event.  Prefer the
        typed helpers (:meth:`record_deprecated_usage`,
        :meth:`record_draft_override`) for standard governance events.
        """
        self._audit_events.append(event)

    def record_deprecated_usage(
        self,
        artifact_type: str,
        artifact_id: str,
        version: str,
        deprecation_reason: str | None = None,
    ) -> None:
        """Record that a DEPRECATED artifact was resolved.

        Args:
            artifact_type:      Canonical artifact type (``"primitive"``, etc.).
            artifact_id:        Stable artifact identifier.
            version:            Resolved version string.
            deprecation_reason: Human-readable reason from the governance block,
                                or ``None`` when not provided.
        """
        self._audit_events.append(GovernanceAuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
            timestamp_utc=datetime.now(timezone.utc),
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            version=version,
            details={"deprecation_reason": deprecation_reason} if deprecation_reason else {},
        ))

    def record_draft_override(
        self,
        artifact_type: str,
        artifact_id: str,
        version: str,
    ) -> None:
        """Record that a DRAFT artifact was resolved under ``allow_draft=True``.

        Args:
            artifact_type: Canonical artifact type.
            artifact_id:   Stable artifact identifier.
            version:       Resolved version string.
        """
        self._audit_events.append(GovernanceAuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AUDIT_EVENT_DRAFT_OVERRIDE_USED,
            timestamp_utc=datetime.now(timezone.utc),
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            version=version,
            details={},
        ))

    # ------------------------------------------------------------------
    # Read surface
    # ------------------------------------------------------------------

    def get_audit_events(self) -> list[GovernanceAuditEvent]:
        """Return a snapshot of accumulated audit events.

        Returns a *copy* of the internal list so callers cannot mutate
        collector state through the returned value.
        """
        return list(self._audit_events)

    def event_count(self) -> int:
        """Return the number of audit events accumulated so far."""
        return len(self._audit_events)

    # ------------------------------------------------------------------
    # Stage tracking
    # ------------------------------------------------------------------

    def mark_stage(self, stage: str) -> None:
        """Update the current pipeline stage for failure attribution.

        Call this just before entering each major stage so that if an
        exception is recorded via :meth:`record_failure_context` the
        stage is correctly attributed.

        Args:
            stage: One of ``"resolution"``, ``"render"``, ``"export"``.
        """
        self._current_stage = stage

    # ------------------------------------------------------------------
    # Usage record accumulation
    # ------------------------------------------------------------------

    def record_artifact_usage(
        self,
        artifact_type: str,
        artifact_family: str,
        artifact_version: str | None,
        lifecycle_state: str | None,
        resolution_source: str,
        usage_scope: str,
        warning_emitted: bool,
        is_draft_override_usage: bool,
    ) -> None:
        """Record that an artifact was resolved during this run.

        Deduplicates by ``(artifact_type, artifact_family, artifact_version,
        usage_scope)``.  When the same key is seen more than once, the
        existing record is **merged** rather than discarded so that no
        governance signal is lost:

        Merge policy:

        - ``warning_emitted``: OR — ``True`` if any observation emitted a
          warning.
        - ``is_draft_override_usage``: OR — ``True`` if any observation used
          a DRAFT override.
        - ``resolution_source``: ``"explicit"`` wins over ``"default"`` — if
          any observation was explicit, the merged record is explicit.
        - All other fields (``lifecycle_state``, ``run_ts``): first observation
          wins.

        Args:
            artifact_type:          Canonical artifact category.
            artifact_family:        Stable artifact identifier.
            artifact_version:       Resolved version, or ``None``.
            lifecycle_state:        Governance state, or ``None``.
            resolution_source:      ``"explicit"`` or ``"default"``.
            usage_scope:            ``"top_level"``, ``"dependency"``,
                                    or ``"per_slide"``.
            warning_emitted:        Whether a deprecation warning was issued.
            is_draft_override_usage: Whether DRAFT was used under override.
        """
        key = (artifact_type, artifact_family, artifact_version, usage_scope)
        if key in self._usage_records:
            # Merge: preserve the strongest observed signal.
            existing = self._usage_records[key]
            if warning_emitted and not existing.warning_emitted:
                existing.warning_emitted = True
            if is_draft_override_usage and not existing.is_draft_override_usage:
                existing.is_draft_override_usage = True
            if resolution_source == "explicit" and existing.resolution_source != "explicit":
                existing.resolution_source = "explicit"
            return
        self._usage_records[key] = ArtifactUsageRecord(
            run_id="",
            run_ts=self._run_ts,
            artifact_type=artifact_type,
            artifact_family=artifact_family,
            artifact_version=artifact_version,
            lifecycle_state=lifecycle_state,
            resolution_source=resolution_source,
            usage_scope=usage_scope,
            warning_emitted=warning_emitted,
            is_draft_override_usage=is_draft_override_usage,
        )

    def get_usage_records(self) -> list[ArtifactUsageRecord]:
        """Return a snapshot of accumulated usage records in insertion order.

        Returns a *copy* of the internal collection.  Records may not yet be
        finalised (``run_id`` is ``""``); call :meth:`finalize_usage` before
        persisting.
        """
        return list(self._usage_records.values())

    def finalize_usage(self, succeeded: bool, run_id: str = "") -> None:
        """Backfill ``run_id`` and set the success/failure flag on all records.

        **Idempotent**: the first call mutates all records in place and sets an
        internal guard.  Subsequent calls are silent no-ops, so it is safe to
        call ``finalize_usage`` from multiple exception handlers in the same
        pipeline run without risk of double-flagging.

        Args:
            succeeded: ``True`` when the run completed without exception.
            run_id:    UUID of the pipeline run; backfilled into each record.
        """
        if self._finalized:
            return
        self._finalized = True
        for rec in self._usage_records.values():
            rec.run_id = run_id
            if succeeded:
                rec.used_in_successful_run = True
            else:
                rec.used_in_failed_run = True

    # ------------------------------------------------------------------
    # Failure attribution
    # ------------------------------------------------------------------

    def record_failure_context(
        self,
        exc: BaseException,
        candidate_type: str | None = None,
        candidate_family: str | None = None,
        candidate_version: str | None = None,
    ) -> None:
        """Capture exception context for failure attribution.

        Call from each resolution-stage ``except`` block before re-raising.
        Only the first call wins (subsequent calls are ignored), so that the
        attribution reflects the root failure, not a secondary cascade.

        Args:
            exc:              The exception that was caught.
            candidate_type:   Artifact type being resolved at failure time.
            candidate_family: Artifact family being resolved at failure time.
            candidate_version: Artifact version being resolved at failure time.
        """
        if self._failure_context is not None:
            return  # First call wins.
        self._failure_context = {
            "exc_type_name": type(exc).__name__,
            "exc_message": str(exc),
            "stage": self._current_stage,
            "candidate_type": candidate_type,
            "candidate_family": candidate_family,
            "candidate_version": candidate_version,
        }

    def get_failure_attribution(
        self,
        run_id: str,
        run_failed: bool,
    ) -> RunFailureAttribution:
        """Build a :class:`~.analytics_models.RunFailureAttribution` from captured context.

        When no failure context has been recorded (successful run or failure
        before context was captured), returns an ``"unknown"``/``"low"``
        attribution.

        Confidence mapping:

        - ``GovernanceViolationError`` → stage ``"governance"``, confidence ``"high"``
        - ``DesignSystemError`` family → stage ``"resolution"``, confidence ``"high"``
        - stage ``"render"`` or ``"export"`` → confidence ``"medium"``
        - anything else → ``"unknown"`` / ``"low"``

        Args:
            run_id:     UUID of the pipeline run.
            run_failed: Whether the run failed.
        """
        if self._failure_context is None:
            return RunFailureAttribution(
                run_id=run_id,
                run_failed=run_failed,
                failure_stage="unknown",
                candidate_artifact_type=None,
                candidate_artifact_family=None,
                candidate_artifact_version=None,
                attribution_confidence="low",
                failure_message_summary=None,
            )

        ctx = self._failure_context
        exc_type_name: str = ctx["exc_type_name"]
        exc_message: str = ctx["exc_message"]
        stage: str = ctx["stage"]

        if exc_type_name in _GOVERNANCE_VIOLATION_NAMES:
            failure_stage = "governance"
            confidence = "high"
        elif exc_type_name in _DESIGN_SYSTEM_ERROR_NAMES:
            failure_stage = "resolution"
            confidence = "high"
        elif stage in ("render", "export"):
            failure_stage = stage
            confidence = "medium"
        else:
            failure_stage = stage if stage else "unknown"
            confidence = "low"

        summary = exc_message[:200] if exc_message else None

        return RunFailureAttribution(
            run_id=run_id,
            run_failed=run_failed,
            failure_stage=failure_stage,
            candidate_artifact_type=ctx["candidate_type"],
            candidate_artifact_family=ctx["candidate_family"],
            candidate_artifact_version=ctx["candidate_version"],
            attribution_confidence=confidence,
            failure_message_summary=summary,
        )
