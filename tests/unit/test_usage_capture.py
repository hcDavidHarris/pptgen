"""Tests for Phase 10D.4 — Usage Capture (ArtifactUsageRecord, RunFailureAttribution,
GovernanceTelemetryCollector extensions, and writer functions).
"""
from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pptgen.analytics import (
    ArtifactUsageRecord,
    GovernanceTelemetryCollector,
    RunFailureAttribution,
    write_failure_attribution,
    write_usage_snapshot,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def now_utc() -> datetime:
    return datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def collector(now_utc: datetime) -> GovernanceTelemetryCollector:
    return GovernanceTelemetryCollector(run_ts=now_utc)


# ---------------------------------------------------------------------------
# ArtifactUsageRecord.to_dict()
# ---------------------------------------------------------------------------


class TestArtifactUsageRecordToDict:
    def test_all_fields_present(self, now_utc: datetime) -> None:
        rec = ArtifactUsageRecord(
            run_id="abc-123",
            run_ts=now_utc,
            artifact_type="primitive",
            artifact_family="two_column",
            artifact_version="1.0.0",
            lifecycle_state="approved",
            resolution_source="explicit",
            usage_scope="top_level",
            warning_emitted=False,
            is_draft_override_usage=False,
            used_in_successful_run=True,
        )
        d = rec.to_dict()
        assert d["run_id"] == "abc-123"
        assert d["artifact_type"] == "primitive"
        assert d["artifact_family"] == "two_column"
        assert d["artifact_version"] == "1.0.0"
        assert d["lifecycle_state"] == "approved"
        assert d["resolution_source"] == "explicit"
        assert d["usage_scope"] == "top_level"
        assert d["warning_emitted"] is False
        assert d["is_draft_override_usage"] is False
        assert d["used_in_successful_run"] is True
        assert d["used_in_failed_run"] is False
        assert "run_ts" in d

    def test_run_ts_iso_format(self, now_utc: datetime) -> None:
        rec = ArtifactUsageRecord(
            run_id="x", run_ts=now_utc,
            artifact_type="theme", artifact_family="executive",
            artifact_version=None, lifecycle_state=None,
            resolution_source="default", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )
        d = rec.to_dict()
        assert isinstance(d["run_ts"], str)
        # Must be parseable as ISO 8601
        datetime.fromisoformat(d["run_ts"])

    def test_none_fields_serialise_as_none(self, now_utc: datetime) -> None:
        rec = ArtifactUsageRecord(
            run_id="", run_ts=now_utc,
            artifact_type="token_set", artifact_family="base",
            artifact_version=None, lifecycle_state=None,
            resolution_source="explicit", usage_scope="dependency",
            warning_emitted=False, is_draft_override_usage=False,
        )
        d = rec.to_dict()
        assert d["artifact_version"] is None
        assert d["lifecycle_state"] is None


# ---------------------------------------------------------------------------
# RunFailureAttribution.to_dict()
# ---------------------------------------------------------------------------


class TestRunFailureAttributionToDict:
    def test_all_fields_present(self) -> None:
        fa = RunFailureAttribution(
            run_id="run-xyz",
            run_failed=True,
            failure_stage="governance",
            candidate_artifact_type="primitive",
            candidate_artifact_family="two_column",
            candidate_artifact_version="1.0.0",
            attribution_confidence="high",
            failure_message_summary="DRAFT artifact blocked",
        )
        d = fa.to_dict()
        assert d["run_id"] == "run-xyz"
        assert d["run_failed"] is True
        assert d["failure_stage"] == "governance"
        assert d["candidate_artifact_type"] == "primitive"
        assert d["candidate_artifact_family"] == "two_column"
        assert d["candidate_artifact_version"] == "1.0.0"
        assert d["attribution_confidence"] == "high"
        assert d["failure_message_summary"] == "DRAFT artifact blocked"

    def test_none_candidates(self) -> None:
        fa = RunFailureAttribution(
            run_id="r", run_failed=True, failure_stage="unknown",
            candidate_artifact_type=None, candidate_artifact_family=None,
            candidate_artifact_version=None,
            attribution_confidence="low", failure_message_summary=None,
        )
        d = fa.to_dict()
        assert d["candidate_artifact_type"] is None
        assert d["candidate_artifact_family"] is None
        assert d["failure_message_summary"] is None

    def test_frozen(self) -> None:
        fa = RunFailureAttribution(
            run_id="r", run_failed=False, failure_stage="unknown",
            candidate_artifact_type=None, candidate_artifact_family=None,
            candidate_artifact_version=None,
            attribution_confidence="low", failure_message_summary=None,
        )
        with pytest.raises((AttributeError, TypeError)):
            fa.run_id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GovernanceTelemetryCollector — usage record accumulation
# ---------------------------------------------------------------------------


class TestCollectorUsageRecords:
    def test_record_artifact_usage_accumulates(self, collector: GovernanceTelemetryCollector, now_utc: datetime) -> None:
        collector.record_artifact_usage(
            artifact_type="primitive", artifact_family="two_column",
            artifact_version="1.0.0", lifecycle_state="approved",
            resolution_source="explicit", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )
        collector.record_artifact_usage(
            artifact_type="layout", artifact_family="two_col_layout",
            artifact_version="1.0.0", lifecycle_state="approved",
            resolution_source="explicit", usage_scope="dependency",
            warning_emitted=False, is_draft_override_usage=False,
        )
        records = collector.get_usage_records()
        assert len(records) == 2
        assert records[0].artifact_type == "primitive"
        assert records[1].artifact_type == "layout"

    def test_dedup_by_type_family_version_scope(self, collector: GovernanceTelemetryCollector) -> None:
        for _ in range(3):
            collector.record_artifact_usage(
                artifact_type="primitive", artifact_family="two_column",
                artifact_version="1.0.0", lifecycle_state="approved",
                resolution_source="explicit", usage_scope="top_level",
                warning_emitted=False, is_draft_override_usage=False,
            )
        assert len(collector.get_usage_records()) == 1

    def test_same_artifact_different_scope_not_deduped(self, collector: GovernanceTelemetryCollector) -> None:
        collector.record_artifact_usage(
            artifact_type="primitive", artifact_family="two_column",
            artifact_version="1.0.0", lifecycle_state="approved",
            resolution_source="explicit", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )
        collector.record_artifact_usage(
            artifact_type="primitive", artifact_family="two_column",
            artifact_version="1.0.0", lifecycle_state="approved",
            resolution_source="explicit", usage_scope="per_slide",
            warning_emitted=False, is_draft_override_usage=False,
        )
        assert len(collector.get_usage_records()) == 2

    def test_run_ts_on_records(self, collector: GovernanceTelemetryCollector, now_utc: datetime) -> None:
        collector.record_artifact_usage(
            artifact_type="theme", artifact_family="executive",
            artifact_version="2.0.0", lifecycle_state="approved",
            resolution_source="default", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )
        rec = collector.get_usage_records()[0]
        assert rec.run_ts == now_utc

    def test_get_usage_records_returns_copy(self, collector: GovernanceTelemetryCollector) -> None:
        collector.record_artifact_usage(
            artifact_type="primitive", artifact_family="fc",
            artifact_version="1.0", lifecycle_state=None,
            resolution_source="explicit", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )
        a = collector.get_usage_records()
        b = collector.get_usage_records()
        assert a is not b

    def test_run_id_empty_before_finalize(self, collector: GovernanceTelemetryCollector) -> None:
        collector.record_artifact_usage(
            artifact_type="primitive", artifact_family="fc",
            artifact_version="1.0", lifecycle_state=None,
            resolution_source="explicit", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )
        rec = collector.get_usage_records()[0]
        assert rec.run_id == ""


# ---------------------------------------------------------------------------
# GovernanceTelemetryCollector — finalize_usage
# ---------------------------------------------------------------------------


class TestCollectorFinalizeUsage:
    def _add_record(self, col: GovernanceTelemetryCollector) -> None:
        col.record_artifact_usage(
            artifact_type="primitive", artifact_family="fc",
            artifact_version="1.0", lifecycle_state="approved",
            resolution_source="explicit", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )

    def test_finalize_success_sets_flag(self, collector: GovernanceTelemetryCollector) -> None:
        self._add_record(collector)
        collector.finalize_usage(True, run_id="run-001")
        rec = collector.get_usage_records()[0]
        assert rec.used_in_successful_run is True
        assert rec.used_in_failed_run is False

    def test_finalize_failure_sets_flag(self, collector: GovernanceTelemetryCollector) -> None:
        self._add_record(collector)
        collector.finalize_usage(False, run_id="run-002")
        rec = collector.get_usage_records()[0]
        assert rec.used_in_successful_run is False
        assert rec.used_in_failed_run is True

    def test_finalize_backfills_run_id(self, collector: GovernanceTelemetryCollector) -> None:
        self._add_record(collector)
        collector.finalize_usage(True, run_id="my-uuid-here")
        rec = collector.get_usage_records()[0]
        assert rec.run_id == "my-uuid-here"

    def test_finalize_noop_on_empty(self, collector: GovernanceTelemetryCollector) -> None:
        # Should not raise when no records accumulated.
        collector.finalize_usage(True, run_id="empty-run")
        assert collector.get_usage_records() == []


# ---------------------------------------------------------------------------
# GovernanceTelemetryCollector — mark_stage + get_failure_attribution
# ---------------------------------------------------------------------------


class TestCollectorFailureAttribution:
    def test_no_context_returns_unknown_low(self, collector: GovernanceTelemetryCollector) -> None:
        fa = collector.get_failure_attribution(run_id="r", run_failed=False)
        assert fa.failure_stage == "unknown"
        assert fa.attribution_confidence == "low"
        assert fa.candidate_artifact_type is None

    def test_governance_violation_gives_governance_high(self, collector: GovernanceTelemetryCollector) -> None:
        from pptgen.design_system.exceptions import GovernanceViolationError
        exc = GovernanceViolationError("DRAFT artifact blocked")
        collector.record_failure_context(exc, candidate_type="primitive",
                                         candidate_family="fc", candidate_version="1.0")
        fa = collector.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "governance"
        assert fa.attribution_confidence == "high"
        assert fa.candidate_artifact_type == "primitive"
        assert fa.candidate_artifact_family == "fc"

    def test_design_system_error_gives_resolution_high(self, collector: GovernanceTelemetryCollector) -> None:
        from pptgen.design_system.exceptions import DesignSystemError
        exc = DesignSystemError("artifact not found")
        collector.record_failure_context(exc, candidate_type="layout",
                                         candidate_family="two_col", candidate_version=None)
        fa = collector.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "resolution"
        assert fa.attribution_confidence == "high"
        assert fa.candidate_artifact_type == "layout"

    def test_render_stage_gives_render_medium(self, collector: GovernanceTelemetryCollector) -> None:
        collector.mark_stage("render")
        exc = RuntimeError("template corrupt")
        collector.record_failure_context(exc)
        fa = collector.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "render"
        assert fa.attribution_confidence == "medium"

    def test_export_stage_gives_export_medium(self, collector: GovernanceTelemetryCollector) -> None:
        collector.mark_stage("export")
        exc = OSError("disk full")
        collector.record_failure_context(exc)
        fa = collector.get_failure_attribution(run_id="r", run_failed=True)
        assert fa.failure_stage == "export"
        assert fa.attribution_confidence == "medium"

    def test_failure_message_summary_truncated(self, collector: GovernanceTelemetryCollector) -> None:
        long_msg = "x" * 500
        exc = ValueError(long_msg)
        collector.record_failure_context(exc)
        fa = collector.get_failure_attribution(run_id="r", run_failed=True)
        assert len(fa.failure_message_summary) == 200

    def test_first_call_wins(self, collector: GovernanceTelemetryCollector) -> None:
        """Second record_failure_context call is ignored."""
        from pptgen.design_system.exceptions import GovernanceViolationError, DesignSystemError
        exc1 = GovernanceViolationError("first")
        exc2 = DesignSystemError("second")
        collector.record_failure_context(exc1, candidate_type="primitive",
                                         candidate_family="fc", candidate_version=None)
        collector.record_failure_context(exc2, candidate_type="layout",
                                         candidate_family="lc", candidate_version=None)
        fa = collector.get_failure_attribution(run_id="r", run_failed=True)
        # Must reflect the first exception (governance)
        assert fa.failure_stage == "governance"
        assert fa.candidate_artifact_type == "primitive"

    def test_run_id_and_run_failed_forwarded(self, collector: GovernanceTelemetryCollector) -> None:
        fa = collector.get_failure_attribution(run_id="uuid-abc", run_failed=True)
        assert fa.run_id == "uuid-abc"
        assert fa.run_failed is True


# ---------------------------------------------------------------------------
# Writer — write_usage_snapshot
# ---------------------------------------------------------------------------


class TestWriteUsageSnapshot:
    def test_writes_json_array(self, tmp_path: Path, now_utc: datetime) -> None:
        rec = ArtifactUsageRecord(
            run_id="run-1", run_ts=now_utc,
            artifact_type="primitive", artifact_family="fc",
            artifact_version="1.0", lifecycle_state="approved",
            resolution_source="explicit", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
            used_in_successful_run=True,
        )
        write_usage_snapshot([rec], tmp_path, "run-1")
        out = tmp_path / "governance" / "usage_runs" / "run-1" / "artifact_usage_snapshot.json"
        assert out.exists()
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["artifact_family"] == "fc"

    def test_noop_when_empty(self, tmp_path: Path) -> None:
        write_usage_snapshot([], tmp_path, "run-empty")
        out = tmp_path / "governance" / "usage_runs" / "run-empty" / "artifact_usage_snapshot.json"
        assert not out.exists()

    def test_creates_directory(self, tmp_path: Path, now_utc: datetime) -> None:
        rec = ArtifactUsageRecord(
            run_id="new-run", run_ts=now_utc,
            artifact_type="theme", artifact_family="executive",
            artifact_version="2.0", lifecycle_state="approved",
            resolution_source="default", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )
        write_usage_snapshot([rec], tmp_path, "new-run")
        assert (tmp_path / "governance" / "usage_runs" / "new-run").is_dir()

    def test_error_does_not_raise(self, tmp_path: Path, now_utc: datetime) -> None:
        """Writer must not raise even when the directory is not writable."""
        rec = ArtifactUsageRecord(
            run_id="r", run_ts=now_utc,
            artifact_type="primitive", artifact_family="fc",
            artifact_version="1.0", lifecycle_state=None,
            resolution_source="explicit", usage_scope="top_level",
            warning_emitted=False, is_draft_override_usage=False,
        )
        # Pass a path that cannot be created (file exists in the way)
        blocker = tmp_path / "governance"
        blocker.write_text("block")
        # Should not raise
        write_usage_snapshot([rec], tmp_path, "r")


# ---------------------------------------------------------------------------
# Writer — write_failure_attribution
# ---------------------------------------------------------------------------


class TestWriteFailureAttribution:
    def test_writes_json_object(self, tmp_path: Path) -> None:
        fa = RunFailureAttribution(
            run_id="run-2", run_failed=True,
            failure_stage="governance",
            candidate_artifact_type="primitive",
            candidate_artifact_family="fc",
            candidate_artifact_version="1.0",
            attribution_confidence="high",
            failure_message_summary="DRAFT blocked",
        )
        write_failure_attribution(fa, tmp_path, "run-2")
        out = tmp_path / "governance" / "usage_runs" / "run-2" / "failure_attribution.json"
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["failure_stage"] == "governance"
        assert data["attribution_confidence"] == "high"

    def test_creates_directory(self, tmp_path: Path) -> None:
        fa = RunFailureAttribution(
            run_id="fa-run", run_failed=True, failure_stage="unknown",
            candidate_artifact_type=None, candidate_artifact_family=None,
            candidate_artifact_version=None,
            attribution_confidence="low", failure_message_summary=None,
        )
        write_failure_attribution(fa, tmp_path, "fa-run")
        assert (tmp_path / "governance" / "usage_runs" / "fa-run").is_dir()

    def test_error_does_not_raise(self, tmp_path: Path) -> None:
        fa = RunFailureAttribution(
            run_id="r", run_failed=False, failure_stage="unknown",
            candidate_artifact_type=None, candidate_artifact_family=None,
            candidate_artifact_version=None,
            attribution_confidence="low", failure_message_summary=None,
        )
        blocker = tmp_path / "governance"
        blocker.write_text("block")
        write_failure_attribution(fa, tmp_path, "r")  # must not raise


# ---------------------------------------------------------------------------
# Integration — usage snapshot written via generate_presentation
# ---------------------------------------------------------------------------


class TestPipelineUsageSnapshot:
    """Integration smoke tests: usage_records populated and snapshot written."""

    def _make_deck_yaml(self, primitive_id: str) -> str:
        return textwrap.dedent(f"""\
            primitive: {primitive_id}
            content:
              title: Hello
            slides:
              - primitive: {primitive_id}
                content:
                  title: Slide 1
        """)

    def _make_design_system(self, tmp_path: Path) -> Path:
        """Create a minimal design system with one primitive."""
        ds = tmp_path / "ds"
        for subdir in ("primitives", "layouts", "tokens", "brands", "themes", "assets"):
            (ds / subdir).mkdir(parents=True)
        (ds / "primitives" / "fc.yaml").write_text(textwrap.dedent("""\
            schema_version: 1
            primitive_id: fc
            version: "1.0.0"
            layout_id: single_column
            constraints:
              allow_extra_content: true
            slots:
              title:
                required: false
                content_type: string
                maps_to: content
                description: Title
            governance:
              status: approved
        """))
        (ds / "layouts" / "single_column.yaml").write_text(textwrap.dedent("""\
            schema_version: 1
            layout_id: single_column
            version: "1.0.0"
            regions:
              content:
                required: false
                label: Main content
            governance:
              status: approved
        """))
        (ds / "tokens" / "base_tokens.yaml").write_text(textwrap.dedent("""\
            schema_version: 1
            version: "1.0.0"
            tokens:
              color.primary: "#000000"
        """))
        return ds

    def test_usage_records_present_on_result(self, tmp_path: Path) -> None:
        """generate_presentation() populates usage_records on the success path."""
        from pptgen.pipeline.generation_pipeline import generate_presentation
        from pptgen.config import RuntimeSettings, override_settings

        ds = self._make_design_system(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(self._make_deck_yaml("fc"))
        finally:
            override_settings(None)

        assert hasattr(result, "usage_records")
        assert isinstance(result.usage_records, list)
        # primitive 'fc' was resolved → at least one usage record
        assert len(result.usage_records) >= 1
        types = [r.artifact_type for r in result.usage_records]
        assert "primitive" in types

    def test_usage_snapshot_written_to_analytics_dir(self, tmp_path: Path) -> None:
        """When analytics_dir is set and governed artifacts are used, snapshot is written."""
        from pptgen.pipeline.generation_pipeline import generate_presentation
        from pptgen.config import RuntimeSettings, override_settings

        ds = self._make_design_system(tmp_path)
        analytics_dir = tmp_path / "analytics"
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            analytics_dir=str(analytics_dir),
        ))
        try:
            result = generate_presentation(self._make_deck_yaml("fc"))
        finally:
            override_settings(None)

        assert result.usage_records, "expected non-empty usage_records"
        snapshot_dir = analytics_dir / "governance" / "usage_runs" / result.run_id
        assert snapshot_dir.is_dir()
        snapshot_file = snapshot_dir / "artifact_usage_snapshot.json"
        assert snapshot_file.exists()
        data = json.loads(snapshot_file.read_text())
        assert isinstance(data, list)
        assert len(data) == len(result.usage_records)
