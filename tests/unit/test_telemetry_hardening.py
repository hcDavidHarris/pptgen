"""Tests for Phase 10D.5 — Telemetry Hardening.

Covers:
- Usage dedup with merge semantics (OR booleans, prefer "explicit")
- Idempotent finalize_usage
- Stage markers and failure attribution classification
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pptgen.analytics import GovernanceTelemetryCollector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col(**kwargs) -> GovernanceTelemetryCollector:
    return GovernanceTelemetryCollector(**kwargs)


def _record(col, *, artifact_type="primitive", artifact_family="fc",
            artifact_version="1.0", lifecycle_state="approved",
            resolution_source="explicit", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False):
    col.record_artifact_usage(
        artifact_type=artifact_type,
        artifact_family=artifact_family,
        artifact_version=artifact_version,
        lifecycle_state=lifecycle_state,
        resolution_source=resolution_source,
        usage_scope=usage_scope,
        warning_emitted=warning_emitted,
        is_draft_override_usage=is_draft_override_usage,
    )


# ---------------------------------------------------------------------------
# Usage merge semantics
# ---------------------------------------------------------------------------

class TestUsageMergeSemantics:
    """Duplicate observations of the same (type, family, version, scope) key
    must merge rather than drop the later signal."""

    def test_first_observation_creates_record(self):
        col = _col()
        _record(col, warning_emitted=False)
        assert len(col.get_usage_records()) == 1

    def test_duplicate_key_does_not_grow_records(self):
        col = _col()
        _record(col)
        _record(col)
        assert len(col.get_usage_records()) == 1

    def test_merge_warning_emitted_or_semantics(self):
        """Second obs with warning_emitted=True must update the record."""
        col = _col()
        _record(col, warning_emitted=False)
        _record(col, warning_emitted=True)   # duplicate key, different signal
        rec = col.get_usage_records()[0]
        assert rec.warning_emitted is True

    def test_merge_warning_stays_false_if_never_emitted(self):
        col = _col()
        _record(col, warning_emitted=False)
        _record(col, warning_emitted=False)
        assert col.get_usage_records()[0].warning_emitted is False

    def test_merge_draft_override_or_semantics(self):
        col = _col()
        _record(col, is_draft_override_usage=False)
        _record(col, is_draft_override_usage=True)
        assert col.get_usage_records()[0].is_draft_override_usage is True

    def test_merge_draft_override_stays_false_if_never_set(self):
        col = _col()
        _record(col, is_draft_override_usage=False)
        _record(col, is_draft_override_usage=False)
        assert col.get_usage_records()[0].is_draft_override_usage is False

    def test_merge_resolution_source_explicit_wins_over_default(self):
        col = _col()
        _record(col, resolution_source="default")
        _record(col, resolution_source="explicit")
        assert col.get_usage_records()[0].resolution_source == "explicit"

    def test_merge_resolution_source_explicit_then_default_stays_explicit(self):
        col = _col()
        _record(col, resolution_source="explicit")
        _record(col, resolution_source="default")
        assert col.get_usage_records()[0].resolution_source == "explicit"

    def test_merge_lifecycle_state_first_wins(self):
        col = _col()
        _record(col, lifecycle_state="approved")
        _record(col, lifecycle_state="deprecated")  # second obs ignored for state
        assert col.get_usage_records()[0].lifecycle_state == "approved"

    def test_different_scope_creates_separate_records(self):
        """Usage scope is part of the dedup key — different scopes coexist."""
        col = _col()
        _record(col, usage_scope="top_level")
        _record(col, usage_scope="per_slide")
        assert len(col.get_usage_records()) == 2

    def test_different_version_creates_separate_records(self):
        col = _col()
        _record(col, artifact_version="1.0")
        _record(col, artifact_version="2.0")
        assert len(col.get_usage_records()) == 2

    def test_merge_preserves_insertion_order(self):
        """Records appear in first-seen order regardless of merges."""
        col = _col()
        _record(col, artifact_family="alpha")
        _record(col, artifact_family="beta")
        _record(col, artifact_family="alpha")  # merge, not new
        families = [r.artifact_family for r in col.get_usage_records()]
        assert families == ["alpha", "beta"]

    def test_get_usage_records_returns_copy(self):
        col = _col()
        _record(col)
        a = col.get_usage_records()
        b = col.get_usage_records()
        assert a is not b


# ---------------------------------------------------------------------------
# Idempotent finalization
# ---------------------------------------------------------------------------

class TestIdempotentFinalization:
    def test_first_finalize_sets_success_flag(self):
        col = _col()
        _record(col)
        col.finalize_usage(True, run_id="r1")
        assert col.get_usage_records()[0].used_in_successful_run is True

    def test_second_finalize_is_noop(self):
        col = _col()
        _record(col)
        col.finalize_usage(True, run_id="r1")
        col.finalize_usage(False, run_id="r1")  # second call must be ignored
        rec = col.get_usage_records()[0]
        assert rec.used_in_successful_run is True
        assert rec.used_in_failed_run is False  # not set by second call

    def test_finalize_success_then_failure_noop(self):
        col = _col()
        _record(col)
        col.finalize_usage(True, run_id="run")
        col.finalize_usage(False, run_id="run")  # must not flip the flag
        rec = col.get_usage_records()[0]
        assert rec.used_in_successful_run is True
        assert rec.used_in_failed_run is False

    def test_finalize_failure_then_success_noop(self):
        col = _col()
        _record(col)
        col.finalize_usage(False, run_id="run")
        col.finalize_usage(True, run_id="run")
        rec = col.get_usage_records()[0]
        assert rec.used_in_successful_run is False
        assert rec.used_in_failed_run is True

    def test_finalize_run_id_backfill_idempotent(self):
        col = _col()
        _record(col)
        col.finalize_usage(True, run_id="first-id")
        col.finalize_usage(True, run_id="second-id")  # must not overwrite
        assert col.get_usage_records()[0].run_id == "first-id"

    def test_finalize_empty_records_is_safe(self):
        col = _col()
        col.finalize_usage(True, run_id="r")  # no records — must not raise
        col.finalize_usage(False, run_id="r")  # idempotent on empty too

    def test_multiple_records_all_finalized(self):
        col = _col()
        _record(col, artifact_family="a")
        _record(col, artifact_family="b")
        col.finalize_usage(True, run_id="batch")
        for rec in col.get_usage_records():
            assert rec.run_id == "batch"
            assert rec.used_in_successful_run is True


# ---------------------------------------------------------------------------
# Repeated failure context — first-call-wins
# ---------------------------------------------------------------------------

class TestFailureContextFirstCallWins:
    def test_first_call_captured(self):
        from pptgen.design_system.exceptions import GovernanceViolationError
        col = _col()
        col.record_failure_context(
            GovernanceViolationError("first"), candidate_type="primitive",
            candidate_family="fc", candidate_version="1.0"
        )
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "governance"
        assert fa.candidate_artifact_type == "primitive"

    def test_second_call_ignored(self):
        from pptgen.design_system.exceptions import GovernanceViolationError, DesignSystemError
        col = _col()
        col.record_failure_context(
            GovernanceViolationError("first"), candidate_type="primitive",
            candidate_family="fc", candidate_version=None
        )
        col.record_failure_context(
            DesignSystemError("second"), candidate_type="layout",
            candidate_family="lc", candidate_version=None
        )
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        # First call (governance) wins — second call (resolution) is ignored.
        assert fa.failure_stage == "governance"
        assert fa.candidate_artifact_type == "primitive"

    def test_no_context_gives_unknown_low(self):
        col = _col()
        fa = col.get_failure_attribution(run_id="r", run_failed=False)
        assert fa.failure_stage == "unknown"
        assert fa.attribution_confidence == "low"


# ---------------------------------------------------------------------------
# Stage markers and failure attribution classification
# ---------------------------------------------------------------------------

class TestStageClassification:
    def test_governance_violation_always_governance_high(self):
        """GovernanceViolationError → 'governance'/'high' regardless of stage."""
        from pptgen.design_system.exceptions import GovernanceViolationError
        col = _col()
        col.mark_stage("resolution")
        col.record_failure_context(GovernanceViolationError("draft blocked"))
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "governance"
        assert fa.attribution_confidence == "high"

    def test_design_system_error_always_resolution_high(self):
        """DesignSystemError → 'resolution'/'high' regardless of stage."""
        from pptgen.design_system.exceptions import DesignSystemError
        col = _col()
        col.mark_stage("render")  # stage is render, but exception overrides
        col.record_failure_context(DesignSystemError("not found"))
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "resolution"
        assert fa.attribution_confidence == "high"

    def test_generic_error_at_resolution_stage_low(self):
        col = _col()
        col.mark_stage("resolution")
        col.record_failure_context(RuntimeError("unexpected"))
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "resolution"
        assert fa.attribution_confidence == "low"

    def test_render_stage_gives_medium(self):
        col = _col()
        col.mark_stage("render")
        col.record_failure_context(RuntimeError("pptx corrupt"))
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "render"
        assert fa.attribution_confidence == "medium"

    def test_export_stage_gives_medium(self):
        col = _col()
        col.mark_stage("export")
        col.record_failure_context(OSError("disk full"))
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "export"
        assert fa.attribution_confidence == "medium"

    def test_default_stage_is_resolution(self):
        """Collector initialises with stage='resolution'."""
        col = _col()
        col.record_failure_context(RuntimeError("early failure"))
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "resolution"

    def test_mark_stage_updates_stage(self):
        col = _col()
        col.mark_stage("render")
        assert col._current_stage == "render"
        col.mark_stage("export")
        assert col._current_stage == "export"

    def test_attribution_failure_message_summary_truncated_at_200(self):
        col = _col()
        col.record_failure_context(ValueError("x" * 500))
        fa = col.get_failure_attribution(run_id="r", run_failed=True)
        assert len(fa.failure_message_summary) == 200

    def test_attribution_carries_run_id_and_run_failed(self):
        col = _col()
        fa = col.get_failure_attribution(run_id="uuid-abc", run_failed=True)
        assert fa.run_id == "uuid-abc"
        assert fa.run_failed is True
