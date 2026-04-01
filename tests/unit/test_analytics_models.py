"""Unit tests for Phase 10D.1 — analytics data models.

Covers:
FailureAttribution
- construction with all fields
- construction with artifact_id=None
- to_dict() serialises all fields
- from_dict() round-trips correctly
- from_dict() tolerates missing optional artifact_id

ArtifactUsageEvent
- construction with all fields
- None version and lifecycle_status handled
- to_dict() / from_dict() round-trip
- was_default and run_succeeded serialise as booleans

GovernanceAuditEvent
- construction with required fields only (all optional fields default)
- to_dict() serialises timestamp_utc as ISO 8601 string
- from_dict() parses ISO 8601 string back to datetime
- from_dict() accepts pre-parsed datetime
- details dict is shallow-copied in to_dict()
- details defaults to empty dict
- is NOT hashable (raises TypeError)
- all AUDIT_EVENT_* constants are non-empty strings

RunRecord
- construction with failure_attribution=None
- construction with a nested FailureAttribution
- to_dict() / from_dict() round-trip (no attribution)
- to_dict() / from_dict() round-trip (with nested attribution)
- from_dict() parses ISO 8601 timestamp
- dependency_count is preserved as int

Cross-model
- from_dict(to_dict(x)) produces an equivalent instance for all four types
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from pptgen.analytics import (
    AUDIT_EVENT_DEFAULT_VERSION_CHANGED,
    AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
    AUDIT_EVENT_DRAFT_OVERRIDE_USED,
    AUDIT_EVENT_RUN_COMPLETED,
    AUDIT_EVENT_RUN_FAILED,
    AUDIT_EVENT_VERSION_CREATED,
    AUDIT_EVENT_VERSION_DEPRECATED,
    AUDIT_EVENT_VERSION_PROMOTED,
    ArtifactUsageEvent,
    FailureAttribution,
    GovernanceAuditEvent,
    RunRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime(2026, 3, 27, 12, 0, 0, tzinfo=timezone.utc)
_TS_ISO = "2026-03-27T12:00:00+00:00"


def _make_attribution(**kwargs) -> FailureAttribution:
    defaults = dict(
        stage="layout",
        artifact_type="layout",
        artifact_id="executive",
        error_type="GovernanceViolationError",
    )
    return FailureAttribution(**{**defaults, **kwargs})


def _make_usage_event(**kwargs) -> ArtifactUsageEvent:
    defaults = dict(
        run_id="run-001",
        artifact_type="layout",
        artifact_id="executive",
        version="1.0.0",
        lifecycle_status="approved",
        was_default=True,
        run_succeeded=True,
    )
    return ArtifactUsageEvent(**{**defaults, **kwargs})


def _make_audit_event(**kwargs) -> GovernanceAuditEvent:
    defaults = dict(
        event_id="evt-001",
        event_type=AUDIT_EVENT_RUN_COMPLETED,
        timestamp_utc=_TS,
    )
    return GovernanceAuditEvent(**{**defaults, **kwargs})


def _make_run_record(**kwargs) -> RunRecord:
    defaults = dict(
        run_id="run-001",
        timestamp_utc=_TS,
        mode="deterministic",
        playbook_id="executive_summary",
        template_id="hc_default",
        theme_id="executive",
        stage_reached="rendered",
        succeeded=True,
        failure_attribution=None,
        draft_override_active=False,
        dependency_count=3,
    )
    return RunRecord(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# FailureAttribution
# ---------------------------------------------------------------------------


class TestFailureAttribution:
    def test_construction_full(self):
        fa = _make_attribution()
        assert fa.stage == "layout"
        assert fa.artifact_type == "layout"
        assert fa.artifact_id == "executive"
        assert fa.error_type == "GovernanceViolationError"

    def test_construction_no_artifact_id(self):
        fa = _make_attribution(artifact_id=None)
        assert fa.artifact_id is None

    def test_to_dict_all_fields(self):
        fa = _make_attribution()
        d = fa.to_dict()
        assert d == {
            "stage": "layout",
            "artifact_type": "layout",
            "artifact_id": "executive",
            "error_type": "GovernanceViolationError",
        }

    def test_to_dict_none_artifact_id(self):
        fa = _make_attribution(artifact_id=None)
        assert fa.to_dict()["artifact_id"] is None

    def test_from_dict_round_trip(self):
        fa = _make_attribution()
        assert FailureAttribution.from_dict(fa.to_dict()) == fa

    def test_from_dict_tolerates_missing_artifact_id(self):
        d = {"stage": "asset", "artifact_type": "asset", "error_type": "UnknownAssetError"}
        fa = FailureAttribution.from_dict(d)
        assert fa.artifact_id is None

    def test_frozen(self):
        fa = _make_attribution()
        with pytest.raises((AttributeError, TypeError)):
            fa.stage = "primitive"  # type: ignore[misc]

    def test_json_serialisable(self):
        fa = _make_attribution()
        # Should not raise
        json.dumps(fa.to_dict())


# ---------------------------------------------------------------------------
# ArtifactUsageEvent
# ---------------------------------------------------------------------------


class TestArtifactUsageEvent:
    def test_construction_full(self):
        ev = _make_usage_event()
        assert ev.run_id == "run-001"
        assert ev.artifact_type == "layout"
        assert ev.artifact_id == "executive"
        assert ev.version == "1.0.0"
        assert ev.lifecycle_status == "approved"
        assert ev.was_default is True
        assert ev.run_succeeded is True

    def test_construction_none_version_and_status(self):
        ev = _make_usage_event(version=None, lifecycle_status=None)
        assert ev.version is None
        assert ev.lifecycle_status is None

    def test_to_dict_keys(self):
        ev = _make_usage_event()
        d = ev.to_dict()
        assert set(d.keys()) == {
            "run_id", "artifact_type", "artifact_id",
            "version", "lifecycle_status", "was_default", "run_succeeded",
        }

    def test_to_dict_booleans_are_bool(self):
        ev = _make_usage_event(was_default=False, run_succeeded=False)
        d = ev.to_dict()
        assert d["was_default"] is False
        assert d["run_succeeded"] is False

    def test_from_dict_round_trip(self):
        ev = _make_usage_event()
        assert ArtifactUsageEvent.from_dict(ev.to_dict()) == ev

    def test_from_dict_round_trip_none_fields(self):
        ev = _make_usage_event(version=None, lifecycle_status=None)
        assert ArtifactUsageEvent.from_dict(ev.to_dict()) == ev

    def test_frozen(self):
        ev = _make_usage_event()
        with pytest.raises((AttributeError, TypeError)):
            ev.run_id = "other"  # type: ignore[misc]

    def test_json_serialisable(self):
        ev = _make_usage_event()
        json.dumps(ev.to_dict())

    @pytest.mark.parametrize("artifact_type", [
        "primitive", "layout", "theme", "token_set", "asset",
    ])
    def test_all_artifact_types_accepted(self, artifact_type):
        ev = _make_usage_event(artifact_type=artifact_type)
        assert ev.artifact_type == artifact_type


# ---------------------------------------------------------------------------
# GovernanceAuditEvent
# ---------------------------------------------------------------------------


class TestGovernanceAuditEvent:
    def test_construction_required_only(self):
        ev = _make_audit_event()
        assert ev.event_id == "evt-001"
        assert ev.event_type == AUDIT_EVENT_RUN_COMPLETED
        assert ev.timestamp_utc == _TS
        # All optional fields default to None / empty dict
        assert ev.artifact_type is None
        assert ev.artifact_id is None
        assert ev.version is None
        assert ev.run_id is None
        assert ev.actor is None
        assert ev.details == {}

    def test_construction_full(self):
        ev = _make_audit_event(
            artifact_type="primitive",
            artifact_id="bullet_slide",
            version="1.0.0",
            run_id="run-001",
            actor="ci-bot",
            details={"setting_source": "env"},
        )
        assert ev.artifact_type == "primitive"
        assert ev.details["setting_source"] == "env"

    def test_to_dict_timestamp_is_iso_string(self):
        ev = _make_audit_event()
        d = ev.to_dict()
        assert isinstance(d["timestamp_utc"], str)
        assert d["timestamp_utc"] == _TS_ISO

    def test_to_dict_details_is_shallow_copy(self):
        original_details = {"key": "value"}
        ev = _make_audit_event(details=original_details)
        d = ev.to_dict()
        d["details"]["key"] = "mutated"
        # Original details on the event must be unchanged
        assert ev.details["key"] == "value"

    def test_from_dict_parses_iso_string(self):
        ev = _make_audit_event()
        restored = GovernanceAuditEvent.from_dict(ev.to_dict())
        assert restored.timestamp_utc == _TS

    def test_from_dict_accepts_preparsed_datetime(self):
        d = {
            "event_id": "evt-002",
            "event_type": AUDIT_EVENT_RUN_FAILED,
            "timestamp_utc": _TS,  # already a datetime, not a string
        }
        ev = GovernanceAuditEvent.from_dict(d)
        assert ev.timestamp_utc == _TS

    def test_from_dict_round_trip(self):
        ev = _make_audit_event(
            artifact_type="asset",
            artifact_id="icon.check",
            version="2.0.0",
            run_id="run-002",
            actor="david",
            details={"deprecation_reason": "replaced by icon.checkmark"},
        )
        restored = GovernanceAuditEvent.from_dict(ev.to_dict())
        assert restored.event_id == ev.event_id
        assert restored.event_type == ev.event_type
        assert restored.timestamp_utc == ev.timestamp_utc
        assert restored.artifact_type == ev.artifact_type
        assert restored.artifact_id == ev.artifact_id
        assert restored.version == ev.version
        assert restored.run_id == ev.run_id
        assert restored.actor == ev.actor
        assert restored.details == ev.details

    def test_not_hashable(self):
        ev = _make_audit_event()
        with pytest.raises(TypeError):
            hash(ev)

    def test_details_defaults_to_empty_dict(self):
        ev = _make_audit_event()
        assert ev.details == {}

    def test_json_serialisable(self):
        ev = _make_audit_event(details={"key": "value"})
        json.dumps(ev.to_dict())


class TestAuditEventConstants:
    """All AUDIT_EVENT_* constants must be non-empty strings."""

    @pytest.mark.parametrize("constant", [
        AUDIT_EVENT_DRAFT_OVERRIDE_USED,
        AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
        AUDIT_EVENT_RUN_COMPLETED,
        AUDIT_EVENT_RUN_FAILED,
        AUDIT_EVENT_VERSION_CREATED,
        AUDIT_EVENT_VERSION_PROMOTED,
        AUDIT_EVENT_VERSION_DEPRECATED,
        AUDIT_EVENT_DEFAULT_VERSION_CHANGED,
    ])
    def test_constant_is_non_empty_string(self, constant):
        assert isinstance(constant, str)
        assert len(constant) > 0

    def test_constants_are_distinct(self):
        constants = [
            AUDIT_EVENT_DRAFT_OVERRIDE_USED,
            AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
            AUDIT_EVENT_RUN_COMPLETED,
            AUDIT_EVENT_RUN_FAILED,
            AUDIT_EVENT_VERSION_CREATED,
            AUDIT_EVENT_VERSION_PROMOTED,
            AUDIT_EVENT_VERSION_DEPRECATED,
            AUDIT_EVENT_DEFAULT_VERSION_CHANGED,
        ]
        assert len(constants) == len(set(constants))


# ---------------------------------------------------------------------------
# RunRecord
# ---------------------------------------------------------------------------


class TestRunRecord:
    def test_construction_no_attribution(self):
        rr = _make_run_record()
        assert rr.run_id == "run-001"
        assert rr.succeeded is True
        assert rr.failure_attribution is None
        assert rr.dependency_count == 3
        assert rr.draft_override_active is False

    def test_construction_with_attribution(self):
        fa = _make_attribution()
        rr = _make_run_record(succeeded=False, failure_attribution=fa)
        assert rr.failure_attribution is fa
        assert rr.succeeded is False

    def test_to_dict_no_attribution(self):
        rr = _make_run_record()
        d = rr.to_dict()
        assert d["failure_attribution"] is None
        assert isinstance(d["timestamp_utc"], str)
        assert d["dependency_count"] == 3

    def test_to_dict_with_attribution(self):
        fa = _make_attribution()
        rr = _make_run_record(succeeded=False, failure_attribution=fa)
        d = rr.to_dict()
        assert isinstance(d["failure_attribution"], dict)
        assert d["failure_attribution"]["stage"] == "layout"

    def test_from_dict_round_trip_no_attribution(self):
        rr = _make_run_record()
        restored = RunRecord.from_dict(rr.to_dict())
        assert restored == rr

    def test_from_dict_round_trip_with_attribution(self):
        fa = _make_attribution()
        rr = _make_run_record(succeeded=False, failure_attribution=fa)
        restored = RunRecord.from_dict(rr.to_dict())
        assert restored == rr
        assert restored.failure_attribution == fa

    def test_from_dict_parses_iso_timestamp(self):
        rr = _make_run_record()
        d = rr.to_dict()
        assert isinstance(d["timestamp_utc"], str)
        restored = RunRecord.from_dict(d)
        assert restored.timestamp_utc == _TS

    def test_from_dict_preserves_dependency_count_as_int(self):
        rr = _make_run_record(dependency_count=7)
        restored = RunRecord.from_dict(rr.to_dict())
        assert restored.dependency_count == 7
        assert isinstance(restored.dependency_count, int)

    def test_from_dict_optional_fields_none(self):
        rr = _make_run_record(template_id=None, theme_id=None)
        restored = RunRecord.from_dict(rr.to_dict())
        assert restored.template_id is None
        assert restored.theme_id is None

    def test_frozen(self):
        rr = _make_run_record()
        with pytest.raises((AttributeError, TypeError)):
            rr.run_id = "other"  # type: ignore[misc]

    def test_json_serialisable(self):
        rr = _make_run_record(failure_attribution=_make_attribution())
        json.dumps(rr.to_dict())


# ---------------------------------------------------------------------------
# Cross-model round-trip invariant
# ---------------------------------------------------------------------------


class TestRoundTripInvariant:
    """from_dict(to_dict(x)) == x for all four model types."""

    def test_failure_attribution_round_trip(self):
        original = _make_attribution(artifact_id=None)
        assert FailureAttribution.from_dict(original.to_dict()) == original

    def test_artifact_usage_event_round_trip(self):
        original = _make_usage_event(version=None, lifecycle_status=None, was_default=False)
        assert ArtifactUsageEvent.from_dict(original.to_dict()) == original

    def test_governance_audit_event_round_trip(self):
        original = _make_audit_event(
            artifact_type="token_set",
            artifact_id="base",
            version="1.0.0",
            run_id="run-999",
            actor="automation",
            details={"setting_source": "env"},
        )
        restored = GovernanceAuditEvent.from_dict(original.to_dict())
        # Cannot use == directly due to unhashable dict field — compare field by field
        assert restored.event_id == original.event_id
        assert restored.event_type == original.event_type
        assert restored.timestamp_utc == original.timestamp_utc
        assert restored.artifact_type == original.artifact_type
        assert restored.artifact_id == original.artifact_id
        assert restored.version == original.version
        assert restored.run_id == original.run_id
        assert restored.actor == original.actor
        assert restored.details == original.details

    def test_run_record_round_trip_with_attribution(self):
        fa = FailureAttribution(
            stage="asset",
            artifact_type="asset",
            artifact_id="icon.warning",
            error_type="UnknownAssetError",
        )
        original = _make_run_record(
            succeeded=False,
            failure_attribution=fa,
            draft_override_active=True,
            dependency_count=0,
        )
        assert RunRecord.from_dict(original.to_dict()) == original
