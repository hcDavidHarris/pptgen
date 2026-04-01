"""Analytics package — Phase 10D.

Governance analytics and audit layer for the pptgen platform.

Public API::

    from pptgen.analytics import (
        # Data models
        FailureAttribution,
        ArtifactUsageEvent,
        ArtifactUsageRecord,
        GovernanceAuditEvent,
        RunRecord,
        RunFailureAttribution,
        # Aggregate model (Phase 10D.5)
        ArtifactVersionUsageAggregate,
        # Audit event type constants
        AUDIT_EVENT_DRAFT_OVERRIDE_USED,
        AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
        AUDIT_EVENT_RUN_COMPLETED,
        AUDIT_EVENT_RUN_FAILED,
        AUDIT_EVENT_VERSION_CREATED,
        AUDIT_EVENT_VERSION_PROMOTED,
        AUDIT_EVENT_VERSION_DEPRECATED,
        AUDIT_EVENT_DEFAULT_VERSION_CHANGED,
        # Telemetry collector (Phase 10D.5)
        GovernanceTelemetryCollector,
        # Writer (Phase 10D.4)
        write_run_record,
        write_usage_events,
        update_aggregates,
        write_usage_snapshot,
        write_failure_attribution,
        # Aggregate summariser (Phase 10D.5)
        build_daily_aggregates,
        update_daily_aggregates,
        rebuild_all_aggregates,
    )
"""

from .aggregate_models import ArtifactVersionUsageAggregate
from .aggregate_summarizer import (
    build_daily_aggregates,
    rebuild_all_aggregates,
    update_daily_aggregates,
)
from .analytics_models import (
    AUDIT_EVENT_DEFAULT_VERSION_CHANGED,
    AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
    AUDIT_EVENT_DRAFT_OVERRIDE_USED,
    AUDIT_EVENT_RUN_COMPLETED,
    AUDIT_EVENT_RUN_FAILED,
    AUDIT_EVENT_VERSION_CREATED,
    AUDIT_EVENT_VERSION_DEPRECATED,
    AUDIT_EVENT_VERSION_PROMOTED,
    ArtifactUsageEvent,
    ArtifactUsageRecord,
    FailureAttribution,
    GovernanceAuditEvent,
    RunFailureAttribution,
    RunRecord,
)
from .telemetry import GovernanceTelemetryCollector
from .writer import (
    update_aggregates,
    write_audit_events,
    write_failure_attribution,
    write_run_record,
    write_usage_events,
    write_usage_snapshot,
)

__all__ = [
    # Data models
    "FailureAttribution",
    "ArtifactUsageEvent",
    "ArtifactUsageRecord",
    "GovernanceAuditEvent",
    "RunRecord",
    "RunFailureAttribution",
    # Audit event type constants
    "AUDIT_EVENT_DRAFT_OVERRIDE_USED",
    "AUDIT_EVENT_DEPRECATED_ARTIFACT_USED",
    "AUDIT_EVENT_RUN_COMPLETED",
    "AUDIT_EVENT_RUN_FAILED",
    "AUDIT_EVENT_VERSION_CREATED",
    "AUDIT_EVENT_VERSION_PROMOTED",
    "AUDIT_EVENT_VERSION_DEPRECATED",
    "AUDIT_EVENT_DEFAULT_VERSION_CHANGED",
    # Aggregate model
    "ArtifactVersionUsageAggregate",
    # Telemetry collector
    "GovernanceTelemetryCollector",
    # Writer
    "write_audit_events",
    "write_run_record",
    "write_usage_events",
    "update_aggregates",
    "write_usage_snapshot",
    "write_failure_attribution",
    # Aggregate summariser
    "build_daily_aggregates",
    "update_daily_aggregates",
    "rebuild_all_aggregates",
]
