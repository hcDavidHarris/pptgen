"""Unit tests for Phase 10D.5 — Governance Audit Event emission.

Covers:
_enforce_with_audit helper
- approved artifact → no event appended, no warning added
- deprecated artifact → deprecation warning + DEPRECATED_ARTIFACT_USED event
- deprecated artifact with deprecation_reason → reason in event details
- deprecated artifact with no governance block → no reason in details
- draft artifact, allow_draft=False → GovernanceViolationError raised, no event
- draft artifact, allow_draft=True → DRAFT_OVERRIDE_USED event appended
- deprecated artifact + allow_draft=True → DEPRECATED event (not draft)

_backfill_run_id helper
- empty list → empty list
- events with run_id=None get run_id set
- original list not mutated
- events with existing run_id are overwritten

PipelineResult.audit_events
- defaults to empty list when constructed directly

generate_presentation() — audit_events integration
- no governed artifacts → audit_events is empty
- deprecated primitive → one DEPRECATED_ARTIFACT_USED in audit_events
- draft primitive + allow_draft → one DRAFT_OVERRIDE_USED in audit_events
- all audit events carry run_id matching result.run_id
- all audit events have non-None event_id
- all audit events have timezone-aware timestamp_utc
- audit_events written to audit_events.jsonl when analytics_dir configured
- audit_events.jsonl not created when analytics_dir is empty
"""
from __future__ import annotations

import json
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pptgen.analytics import (
    AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
    AUDIT_EVENT_DRAFT_OVERRIDE_USED,
    GovernanceAuditEvent,
    GovernanceTelemetryCollector,
)
from pptgen.config import RuntimeSettings, override_settings
from pptgen.design_system.exceptions import GovernanceViolationError
from pptgen.pipeline.generation_pipeline import (
    PipelineResult,
    _backfill_run_id,
    _enforce_with_audit,
    generate_presentation,
)


# ---------------------------------------------------------------------------
# Design-system fixture helpers
# ---------------------------------------------------------------------------

def _make_ds(tmp: Path, primitive_status: str = "approved", deprecation_reason: str | None = None) -> Path:
    """Minimal design_system with governed primitive."""
    ds = tmp / "ds"
    for subdir in ("primitives", "layouts", "tokens", "brands", "themes", "assets"):
        (ds / subdir).mkdir(parents=True)

    gov_lines = f"          status: {primitive_status}"
    if deprecation_reason:
        gov_lines += f"\n          deprecation_reason: \"{deprecation_reason}\""

    (ds / "primitives" / "title_slide.yaml").write_text(textwrap.dedent(f"""\
        schema_version: 1
        primitive_id: title_slide
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
{gov_lines}
    """), encoding="utf-8")

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
    """), encoding="utf-8")

    (ds / "tokens" / "base_tokens.yaml").write_text(textwrap.dedent("""\
        schema_version: 1
        version: "1.0.0"
        tokens:
          color.primary: "#000000"
    """), encoding="utf-8")

    (ds / "brands" / "default.yaml").write_text(textwrap.dedent("""\
        schema_version: 1
        brand_id: default
        version: "1.0.0"
        token_overrides: {}
    """), encoding="utf-8")

    (ds / "themes" / "executive.yaml").write_text(textwrap.dedent("""\
        schema_version: 1
        theme_id: executive
        version: "1.0.0"
        brand_id: default
        governance:
          status: approved
    """), encoding="utf-8")

    return ds


_PRIM_DECK = textwrap.dedent("""\
    primitive: title_slide
    content:
      title: Hello World
    slides:
      - primitive: title_slide
        content:
          title: Slide 1
""")


# ---------------------------------------------------------------------------
# _enforce_with_audit — unit tests using real registry
# ---------------------------------------------------------------------------

class TestEnforceWithAudit:
    """Tests for _enforce_with_audit using GovernanceTelemetryCollector."""

    def _registry(self, tmp_path: Path, status: str = "approved",
                  reason: str | None = None):
        from pptgen.design_system import DesignSystemRegistry
        ds = _make_ds(tmp_path, primitive_status=status, deprecation_reason=reason)
        return DesignSystemRegistry(ds), ds

    def _call(self, registry, status_hint: str = "approved", *,
              allow_draft: bool = False, warnings: list | None = None,
              telemetry: GovernanceTelemetryCollector | None = None):
        """Helper: call _enforce_with_audit with sensible defaults."""
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=allow_draft,
            governance_warnings=warnings if warnings is not None else [],
            telemetry=telemetry if telemetry is not None else GovernanceTelemetryCollector(),
        )

    def test_approved_no_event_no_warning(self, tmp_path):
        registry, _ = self._registry(tmp_path, "approved")
        warnings: list[str] = []
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=False, governance_warnings=warnings, telemetry=telemetry,
        )
        assert warnings == []
        assert telemetry.event_count() == 0

    def test_deprecated_adds_warning_and_event(self, tmp_path):
        registry, _ = self._registry(tmp_path, "deprecated")
        warnings: list[str] = []
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=False, governance_warnings=warnings, telemetry=telemetry,
        )
        events = telemetry.get_audit_events()
        assert len(warnings) == 1
        assert len(events) == 1
        assert events[0].event_type == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED
        assert events[0].artifact_type == "primitive"
        assert events[0].artifact_id == "title_slide"
        assert events[0].version == "1.0.0"

    def test_deprecated_with_reason_in_details(self, tmp_path):
        registry, _ = self._registry(tmp_path, "deprecated", "Use hero_slide instead")
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=False, governance_warnings=[], telemetry=telemetry,
        )
        assert telemetry.get_audit_events()[0].details.get("deprecation_reason") == "Use hero_slide instead"

    def test_deprecated_no_reason_empty_details(self, tmp_path):
        registry, _ = self._registry(tmp_path, "deprecated", None)
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=False, governance_warnings=[], telemetry=telemetry,
        )
        assert telemetry.get_audit_events()[0].details == {}

    def test_draft_allow_false_raises_no_event(self, tmp_path):
        registry, _ = self._registry(tmp_path, "draft")
        telemetry = GovernanceTelemetryCollector()
        with pytest.raises(GovernanceViolationError):
            _enforce_with_audit(
                registry, "primitive", "title_slide", "1.0.0",
                allow_draft=False, governance_warnings=[], telemetry=telemetry,
            )
        assert telemetry.event_count() == 0

    def test_draft_allow_true_emits_override_event(self, tmp_path):
        registry, _ = self._registry(tmp_path, "draft")
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=True, governance_warnings=[], telemetry=telemetry,
        )
        events = telemetry.get_audit_events()
        assert len(events) == 1
        assert events[0].event_type == AUDIT_EVENT_DRAFT_OVERRIDE_USED
        assert events[0].artifact_type == "primitive"
        assert events[0].artifact_id == "title_slide"

    def test_draft_override_event_has_empty_details(self, tmp_path):
        registry, _ = self._registry(tmp_path, "draft")
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=True, governance_warnings=[], telemetry=telemetry,
        )
        assert telemetry.get_audit_events()[0].details == {}

    def test_deprecated_with_allow_draft_true_emits_deprecated_not_draft(self, tmp_path):
        # deprecated + allow_draft=True → only deprecated event (warning was added)
        registry, _ = self._registry(tmp_path, "deprecated")
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=True, governance_warnings=[], telemetry=telemetry,
        )
        events = telemetry.get_audit_events()
        assert len(events) == 1
        assert events[0].event_type == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED

    def test_event_run_id_is_none_before_backfill(self, tmp_path):
        registry, _ = self._registry(tmp_path, "deprecated")
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=False, governance_warnings=[], telemetry=telemetry,
        )
        assert telemetry.get_audit_events()[0].run_id is None

    def test_event_has_non_empty_event_id(self, tmp_path):
        registry, _ = self._registry(tmp_path, "deprecated")
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=False, governance_warnings=[], telemetry=telemetry,
        )
        assert telemetry.get_audit_events()[0].event_id  # non-empty string

    def test_event_timestamp_is_timezone_aware(self, tmp_path):
        registry, _ = self._registry(tmp_path, "deprecated")
        telemetry = GovernanceTelemetryCollector()
        _enforce_with_audit(
            registry, "primitive", "title_slide", "1.0.0",
            allow_draft=False, governance_warnings=[], telemetry=telemetry,
        )
        assert telemetry.get_audit_events()[0].timestamp_utc.tzinfo is not None


# ---------------------------------------------------------------------------
# GovernanceTelemetryCollector — unit tests
# ---------------------------------------------------------------------------

class TestGovernanceTelemetryCollector:
    """Validate that the collector correctly accumulates and surfaces events."""

    def test_starts_empty(self):
        c = GovernanceTelemetryCollector()
        assert c.get_audit_events() == []
        assert c.event_count() == 0

    def test_record_deprecated_usage_accumulates(self):
        c = GovernanceTelemetryCollector()
        c.record_deprecated_usage("primitive", "title_slide", "1.0.0")
        events = c.get_audit_events()
        assert len(events) == 1
        assert events[0].event_type == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED
        assert events[0].artifact_type == "primitive"
        assert events[0].artifact_id == "title_slide"
        assert events[0].version == "1.0.0"

    def test_record_deprecated_usage_with_reason(self):
        c = GovernanceTelemetryCollector()
        c.record_deprecated_usage("layout", "hero", "2.0.0", "Use card_layout instead")
        ev = c.get_audit_events()[0]
        assert ev.details == {"deprecation_reason": "Use card_layout instead"}

    def test_record_deprecated_usage_no_reason_empty_details(self):
        c = GovernanceTelemetryCollector()
        c.record_deprecated_usage("theme", "classic", "1.0.0", None)
        ev = c.get_audit_events()[0]
        assert ev.details == {}

    def test_record_draft_override_accumulates(self):
        c = GovernanceTelemetryCollector()
        c.record_draft_override("primitive", "wip_slide", "0.1.0")
        events = c.get_audit_events()
        assert len(events) == 1
        assert events[0].event_type == AUDIT_EVENT_DRAFT_OVERRIDE_USED
        assert events[0].artifact_id == "wip_slide"
        assert events[0].details == {}

    def test_multiple_events_accumulated_in_order(self):
        c = GovernanceTelemetryCollector()
        c.record_deprecated_usage("primitive", "old_slide", "1.0.0")
        c.record_draft_override("layout", "wip_layout", "0.1.0")
        c.record_deprecated_usage("theme", "old_theme", "1.0.0")
        events = c.get_audit_events()
        assert len(events) == 3
        assert events[0].event_type == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED
        assert events[1].event_type == AUDIT_EVENT_DRAFT_OVERRIDE_USED
        assert events[2].event_type == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED

    def test_get_audit_events_returns_copy(self):
        """Mutating the returned list must not affect collector state."""
        c = GovernanceTelemetryCollector()
        c.record_draft_override("primitive", "x", "1.0.0")
        snapshot = c.get_audit_events()
        snapshot.clear()
        assert c.event_count() == 1  # collector unaffected

    def test_event_count_matches_get_audit_events(self):
        c = GovernanceTelemetryCollector()
        c.record_deprecated_usage("primitive", "a", "1.0.0")
        c.record_deprecated_usage("layout", "b", "1.0.0")
        assert c.event_count() == len(c.get_audit_events()) == 2

    def test_events_have_unique_event_ids(self):
        c = GovernanceTelemetryCollector()
        c.record_deprecated_usage("primitive", "a", "1.0.0")
        c.record_deprecated_usage("primitive", "b", "1.0.0")
        ids = [e.event_id for e in c.get_audit_events()]
        assert ids[0] != ids[1]

    def test_events_have_timezone_aware_timestamps(self):
        c = GovernanceTelemetryCollector()
        c.record_draft_override("primitive", "x", "1.0.0")
        assert c.get_audit_events()[0].timestamp_utc.tzinfo is not None

    def test_events_start_with_run_id_none(self):
        """run_id is backfilled by _backfill_run_id after resolution."""
        c = GovernanceTelemetryCollector()
        c.record_deprecated_usage("primitive", "x", "1.0.0")
        assert c.get_audit_events()[0].run_id is None

    def test_no_duplicate_events_from_collector(self, tmp_path):
        """Calling record_deprecated_usage twice produces two distinct events
        (dedup is the caller's responsibility via already_governed sets)."""
        c = GovernanceTelemetryCollector()
        c.record_deprecated_usage("primitive", "same", "1.0.0")
        c.record_deprecated_usage("primitive", "same", "1.0.0")
        assert c.event_count() == 2  # collector accumulates; pipeline deduplicates

    def test_pipeline_audit_events_identical_to_direct_collection(self, tmp_path):
        """generate_presentation with deprecated primitive produces same
        audit structure as manually calling the collector methods."""
        ds = _make_ds(tmp_path, "deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        # Must have exactly one DEPRECATED_ARTIFACT_USED for title_slide
        dep_events = [
            e for e in result.audit_events
            if e.event_type == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED
            and e.artifact_id == "title_slide"
        ]
        assert len(dep_events) == 1
        # All events must carry the pipeline run_id
        assert all(e.run_id == result.run_id for e in result.audit_events)


# ---------------------------------------------------------------------------
# _backfill_run_id — unit tests
# ---------------------------------------------------------------------------

def _make_audit_event(run_id: str | None = None) -> GovernanceAuditEvent:
    return GovernanceAuditEvent(
        event_id=str(uuid.uuid4()),
        event_type=AUDIT_EVENT_DEPRECATED_ARTIFACT_USED,
        timestamp_utc=datetime.now(timezone.utc),
        run_id=run_id,
    )


class TestBackfillRunId:
    def test_empty_list_returns_empty(self):
        assert _backfill_run_id([], "run-x") == []

    def test_run_id_set_on_all_events(self):
        events = [_make_audit_event(None), _make_audit_event(None)]
        filled = _backfill_run_id(events, "my-run-id")
        assert all(e.run_id == "my-run-id" for e in filled)

    def test_original_list_not_mutated(self):
        events = [_make_audit_event(None)]
        _backfill_run_id(events, "my-run-id")
        assert events[0].run_id is None  # original unchanged

    def test_returns_new_list_same_length(self):
        events = [_make_audit_event(None), _make_audit_event(None)]
        filled = _backfill_run_id(events, "x")
        assert len(filled) == 2
        assert filled is not events

    def test_overwrites_existing_run_id(self):
        events = [_make_audit_event("old-id")]
        filled = _backfill_run_id(events, "new-id")
        assert filled[0].run_id == "new-id"

    def test_other_fields_preserved(self):
        ev = _make_audit_event(None)
        filled = _backfill_run_id([ev], "run-abc")[0]
        assert filled.event_id == ev.event_id
        assert filled.event_type == ev.event_type
        assert filled.timestamp_utc == ev.timestamp_utc


# ---------------------------------------------------------------------------
# PipelineResult — audit_events field default
# ---------------------------------------------------------------------------

class TestPipelineResultAuditEventsDefault:
    def test_audit_events_defaults_to_empty_list(self):
        result = PipelineResult(stage="deck_planned", playbook_id="x", input_text="y")
        assert result.audit_events == []

    def test_audit_events_accepts_list(self):
        ev = _make_audit_event("run-1")
        result = PipelineResult(
            stage="deck_planned", playbook_id="x", input_text="y",
            audit_events=[ev],
        )
        assert len(result.audit_events) == 1


# ---------------------------------------------------------------------------
# generate_presentation() — audit_events integration
# ---------------------------------------------------------------------------

class TestGeneratePresentationAuditEvents:
    def test_no_governance_events_empty_audit(self, tmp_path):
        ds = _make_ds(tmp_path, "approved")
        deck = textwrap.dedent("""\
            slides:
              - type: content
                content: hello
        """)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(deck)
        finally:
            override_settings(None)
        assert result.audit_events == []

    def test_approved_primitive_no_audit_events(self, tmp_path):
        ds = _make_ds(tmp_path, "approved")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert result.audit_events == []

    def test_deprecated_primitive_emits_audit_event(self, tmp_path):
        ds = _make_ds(tmp_path, "deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert len(result.audit_events) >= 1
        types = [e.event_type for e in result.audit_events]
        assert AUDIT_EVENT_DEPRECATED_ARTIFACT_USED in types

    def test_draft_override_emits_audit_event(self, tmp_path):
        ds = _make_ds(tmp_path, "draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=True,
        ))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert len(result.audit_events) >= 1
        types = [e.event_type for e in result.audit_events]
        assert AUDIT_EVENT_DRAFT_OVERRIDE_USED in types

    def test_audit_events_run_id_matches_result_run_id(self, tmp_path):
        ds = _make_ds(tmp_path, "deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        for ev in result.audit_events:
            assert ev.run_id == result.run_id

    def test_audit_events_have_non_empty_event_id(self, tmp_path):
        ds = _make_ds(tmp_path, "deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        for ev in result.audit_events:
            assert ev.event_id  # non-empty string

    def test_audit_events_have_timezone_aware_timestamp(self, tmp_path):
        ds = _make_ds(tmp_path, "deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        for ev in result.audit_events:
            assert ev.timestamp_utc.tzinfo is not None

    def test_audit_events_written_to_file_when_analytics_dir_set(self, tmp_path):
        ds = _make_ds(tmp_path, "deprecated")
        analytics = tmp_path / "analytics"
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            analytics_dir=str(analytics),
        ))
        try:
            generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        audit_file = analytics / "audit_events.jsonl"
        assert audit_file.exists()
        lines = [ln for ln in audit_file.read_text().splitlines() if ln.strip()]
        assert len(lines) >= 1
        record = json.loads(lines[0])
        assert record["event_type"] == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED

    def test_audit_events_not_written_when_analytics_dir_empty(self, tmp_path):
        ds = _make_ds(tmp_path, "deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds), analytics_dir=""))
        try:
            generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        # No analytics dir created at all
        assert not (tmp_path / "analytics").exists()

    def test_audit_event_artifact_fields_correct(self, tmp_path):
        ds = _make_ds(tmp_path, "deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        deprecated_events = [
            e for e in result.audit_events
            if e.event_type == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED
        ]
        assert len(deprecated_events) >= 1
        ev = deprecated_events[0]
        assert ev.artifact_type == "primitive"
        assert ev.artifact_id == "title_slide"
        assert ev.version == "1.0.0"

    def test_no_duplicate_deprecated_event_for_top_level_and_per_slide(self, tmp_path):
        """Top-level primitive + same primitive in per-slide → one deprecation event."""
        ds = _make_ds(tmp_path, "deprecated")
        deck = textwrap.dedent("""\
            primitive: title_slide
            content:
              title: Hello World
            slides:
              - primitive: title_slide
                content:
                  title: Slide 1
        """)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(deck)
        finally:
            override_settings(None)
        deprecated_events = [
            e for e in result.audit_events
            if e.event_type == AUDIT_EVENT_DEPRECATED_ARTIFACT_USED
               and e.artifact_id == "title_slide"
        ]
        assert len(deprecated_events) == 1
