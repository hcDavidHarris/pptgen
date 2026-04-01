"""Unit tests for Phase 10D.3 — per-run usage event capture.

Covers:
_build_usage_events helper
- empty dependency_chain → empty list
- one entry → one ArtifactUsageEvent with correct fields
- multiple entries → one event per entry, order preserved
- was_default=True when version matches family default_version
- was_default=False when version does not match
- was_default=False when dep.version is None (no governance block)
- was_default=False when family has no default_version (default_version=None)
- was_default=False on family lookup error (never raises)

PipelineResult — new fields (unit, no pipeline invocation)
- run_record defaults to None
- usage_events defaults to empty list

generate_presentation() — RunRecord
- run_record is always present on success
- run_record.run_id matches result.run_id
- run_record.mode matches requested mode
- run_record.stage_reached is "deck_planned" when no output_path
- run_record.succeeded is True
- run_record.failure_attribution is None
- run_record.draft_override_active reflects settings.allow_draft_artifacts
- run_record.dependency_count is 0 when no design-system keys used
- run_record.dependency_count matches len(dependency_chain) with design system
- run_record.timestamp_utc is a timezone-aware datetime
- run_record.playbook_id is non-empty

generate_presentation() — usage_events
- usage_events is empty when no design-system keys used
- usage_events has one entry per dependency when design system is used
- usage_events[i].run_id matches result.run_id
- usage_events[i].artifact_type matches dependency_chain[i].artifact_type
- usage_events[i].run_succeeded is True on success
- was_default=True when artifact YAML declares matching family.default_version
- was_default=False when no family block in artifact YAML
"""
from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from pptgen.analytics import ArtifactUsageEvent, RunRecord
from pptgen.config import RuntimeSettings, override_settings
from pptgen.design_system.dependency_models import ResolvedArtifactDependency
from pptgen.pipeline.generation_pipeline import (
    PipelineResult,
    _build_usage_events,
    generate_presentation,
)


# ---------------------------------------------------------------------------
# Design-system fixture helpers
# ---------------------------------------------------------------------------

def _make_ds(tmp: Path, primitive_status: str = "approved") -> Path:
    """Minimal design_system without family blocks (was_default=False)."""
    ds = tmp / "ds"
    for subdir in ("primitives", "layouts", "tokens", "brands", "themes", "assets"):
        (ds / subdir).mkdir(parents=True)

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
          status: {primitive_status}
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


def _make_ds_with_family(tmp: Path) -> Path:
    """Design system with family.default_version declared (was_default=True)."""
    ds = _make_ds(tmp)
    # Overwrite primitive with a family block pointing to 1.0.0
    (ds / "primitives" / "title_slide.yaml").write_text(textwrap.dedent("""\
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
          status: approved
        family:
          default_version: "1.0.0"
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
# Minimal settings stub for _build_usage_events unit tests
# ---------------------------------------------------------------------------

def _mock_settings(design_system_root: Path | None = None) -> Any:
    s = MagicMock()
    s.design_system_root = design_system_root or Path("/nonexistent")
    return s


# ---------------------------------------------------------------------------
# _build_usage_events — unit tests
# ---------------------------------------------------------------------------


class TestBuildUsageEventsHelper:
    def test_empty_chain_returns_empty_list(self):
        result = _build_usage_events([], "run-x", True, _mock_settings())
        assert result == []

    def test_single_entry_produces_one_event(self, tmp_path):
        ds = _make_ds(tmp_path)
        settings = RuntimeSettings(design_system_path=str(ds))
        chain = [
            ResolvedArtifactDependency(
                artifact_type="primitive",
                artifact_id="title_slide",
                version="1.0.0",
                lifecycle_status="approved",
                source="primitive",
            )
        ]
        events = _build_usage_events(chain, "run-001", True, settings)
        assert len(events) == 1

    def test_event_fields_match_dependency(self, tmp_path):
        ds = _make_ds(tmp_path)
        settings = RuntimeSettings(design_system_path=str(ds))
        chain = [
            ResolvedArtifactDependency(
                artifact_type="layout",
                artifact_id="single_column",
                version="1.0.0",
                lifecycle_status="approved",
                source="layout",
            )
        ]
        ev = _build_usage_events(chain, "run-002", True, settings)[0]
        assert ev.run_id == "run-002"
        assert ev.artifact_type == "layout"
        assert ev.artifact_id == "single_column"
        assert ev.version == "1.0.0"
        assert ev.lifecycle_status == "approved"
        assert ev.run_succeeded is True

    def test_order_preserved(self, tmp_path):
        ds = _make_ds(tmp_path)
        settings = RuntimeSettings(design_system_path=str(ds))
        chain = [
            ResolvedArtifactDependency("primitive", "title_slide", "1.0.0", "approved", "primitive"),
            ResolvedArtifactDependency("layout", "single_column", "1.0.0", "approved", "layout"),
        ]
        events = _build_usage_events(chain, "run-003", True, settings)
        assert [e.artifact_type for e in events] == ["primitive", "layout"]

    def test_was_default_true_when_family_matches(self, tmp_path):
        ds = _make_ds_with_family(tmp_path)
        settings = RuntimeSettings(design_system_path=str(ds))
        chain = [
            ResolvedArtifactDependency("primitive", "title_slide", "1.0.0", "approved", "primitive"),
        ]
        ev = _build_usage_events(chain, "run-004", True, settings)[0]
        assert ev.was_default is True

    def test_was_default_false_when_no_family_block(self, tmp_path):
        ds = _make_ds(tmp_path)  # no family block → default_version=None
        settings = RuntimeSettings(design_system_path=str(ds))
        chain = [
            ResolvedArtifactDependency("primitive", "title_slide", "1.0.0", "approved", "primitive"),
        ]
        ev = _build_usage_events(chain, "run-005", True, settings)[0]
        assert ev.was_default is False

    def test_was_default_false_when_version_is_none(self, tmp_path):
        ds = _make_ds_with_family(tmp_path)
        settings = RuntimeSettings(design_system_path=str(ds))
        chain = [
            ResolvedArtifactDependency("primitive", "title_slide", None, None, "primitive"),
        ]
        ev = _build_usage_events(chain, "run-006", True, settings)[0]
        assert ev.was_default is False

    def test_was_default_false_on_lookup_error(self):
        """Family lookup failure must never raise — falls back to False."""
        settings = _mock_settings(Path("/does/not/exist"))
        chain = [
            ResolvedArtifactDependency("primitive", "any", "1.0.0", "approved", "primitive"),
        ]
        # Should not raise even though registry path is invalid
        events = _build_usage_events(chain, "run-007", False, settings)
        assert events[0].was_default is False

    def test_run_succeeded_false_propagated(self, tmp_path):
        ds = _make_ds(tmp_path)
        settings = RuntimeSettings(design_system_path=str(ds))
        chain = [
            ResolvedArtifactDependency("layout", "single_column", "1.0.0", "approved", "layout"),
        ]
        ev = _build_usage_events(chain, "run-008", False, settings)[0]
        assert ev.run_succeeded is False

    def test_returns_list_of_artifact_usage_events(self, tmp_path):
        ds = _make_ds(tmp_path)
        settings = RuntimeSettings(design_system_path=str(ds))
        chain = [
            ResolvedArtifactDependency("layout", "single_column", "1.0.0", "approved", "layout"),
        ]
        events = _build_usage_events(chain, "run-009", True, settings)
        assert all(isinstance(e, ArtifactUsageEvent) for e in events)


# ---------------------------------------------------------------------------
# PipelineResult — new field defaults
# ---------------------------------------------------------------------------


class TestPipelineResultAnalyticsDefaults:
    def test_run_record_defaults_to_none(self):
        result = PipelineResult(stage="deck_planned", playbook_id="x", input_text="")
        assert result.run_record is None

    def test_usage_events_defaults_to_empty_list(self):
        result = PipelineResult(stage="deck_planned", playbook_id="x", input_text="")
        assert result.usage_events == []

    def test_explicit_run_record_stored(self):
        rr = RunRecord(
            run_id="r1",
            timestamp_utc=datetime(2026, 3, 27, tzinfo=timezone.utc),
            mode="deterministic",
            playbook_id="p1",
            template_id=None,
            theme_id=None,
            stage_reached="deck_planned",
            succeeded=True,
            failure_attribution=None,
            draft_override_active=False,
            dependency_count=0,
        )
        result = PipelineResult(
            stage="deck_planned", playbook_id="x", input_text="", run_record=rr
        )
        assert result.run_record is rr


# ---------------------------------------------------------------------------
# generate_presentation() — RunRecord
# ---------------------------------------------------------------------------


class TestRunRecord:
    def test_run_record_is_present_on_success(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record is not None

    def test_run_record_is_run_record_type(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert isinstance(result.run_record, RunRecord)

    def test_run_record_run_id_matches_result(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record.run_id == result.run_id

    def test_run_record_mode_is_deterministic(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record.mode == "deterministic"

    def test_run_record_stage_reached_deck_planned(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record.stage_reached == "deck_planned"

    def test_run_record_succeeded_true(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record.succeeded is True

    def test_run_record_failure_attribution_none_on_success(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record.failure_attribution is None

    def test_run_record_draft_override_active_false_by_default(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record.draft_override_active is False

    def test_run_record_draft_override_active_true_when_setting_set(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=True,
        ))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert result.run_record.draft_override_active is True

    def test_run_record_dependency_count_zero_without_design_system(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record.dependency_count == 0

    def test_run_record_dependency_count_matches_chain(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert result.run_record.dependency_count == len(result.dependency_chain)
        assert result.run_record.dependency_count > 0

    def test_run_record_timestamp_is_timezone_aware(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        ts = result.run_record.timestamp_utc
        assert isinstance(ts, datetime)
        assert ts.tzinfo is not None

    def test_run_record_playbook_id_non_empty(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_record.playbook_id != ""


# ---------------------------------------------------------------------------
# generate_presentation() — usage_events
# ---------------------------------------------------------------------------


class TestUsageEvents:
    def test_usage_events_empty_without_design_system(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.usage_events == []

    def test_usage_events_present_with_design_system(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert len(result.usage_events) > 0

    def test_usage_events_count_matches_dependency_chain(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert len(result.usage_events) == len(result.dependency_chain)

    def test_usage_event_run_id_matches_result(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        for ev in result.usage_events:
            assert ev.run_id == result.run_id

    def test_usage_event_artifact_types_match_chain(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        chain_types = [d.artifact_type for d in result.dependency_chain]
        event_types = [e.artifact_type for e in result.usage_events]
        assert event_types == chain_types

    def test_usage_events_run_succeeded_true(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert all(e.run_succeeded is True for e in result.usage_events)

    def test_was_default_true_when_family_declared(self, tmp_path):
        ds = _make_ds_with_family(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        prim_events = [e for e in result.usage_events if e.artifact_type == "primitive"]
        assert len(prim_events) > 0
        assert prim_events[0].was_default is True

    def test_was_default_false_without_family_block(self, tmp_path):
        ds = _make_ds(tmp_path)  # no family block
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        prim_events = [e for e in result.usage_events if e.artifact_type == "primitive"]
        assert len(prim_events) > 0
        assert prim_events[0].was_default is False

    def test_usage_events_are_artifact_usage_event_instances(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert all(isinstance(e, ArtifactUsageEvent) for e in result.usage_events)
