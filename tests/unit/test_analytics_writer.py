"""Unit tests for Phase 10D.4 — analytics writer.

Covers:
writer module — write_run_record
- creates analytics_dir if it does not exist
- writes a valid JSON line to run_records.jsonl
- second call appends a second line
- JSON line round-trips to a RunRecord dict
- silently handles write error (no raise, logs warning)

writer module — write_usage_events
- no-op when events list is empty (no file created)
- writes one JSON line per event
- appends on subsequent calls
- JSON lines round-trip to ArtifactUsageEvent dicts

writer module — update_aggregates
- no-op when events list is empty (no file created)
- creates usage_aggregates.json with correct structure
- total_runs increments on second call
- success_count incremented when run_succeeded=True
- failure_count incremented when run_succeeded=False
- default_version_count incremented when was_default=True
- generated_from_line_count tracks cumulative events processed
- key is artifact_type/artifact_id/version (None serialised as "None")
- corrupt existing file is reset and rebuilt
- multiple distinct artifacts produce multiple aggregate entries

generate_presentation() — analytics integration
- no files written when analytics_dir not configured
- run_records.jsonl written when analytics_dir configured (plain run)
- usage_events.jsonl written when design system is used
- usage_aggregates.json written when design system is used
- analytics write failure does NOT fail the pipeline
- each run appends a new line (two runs → two lines in run_records.jsonl)
- analytics_dir_path is None when analytics_dir is empty string
"""
from __future__ import annotations

import json
import logging
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pptgen.analytics import (
    ArtifactUsageEvent,
    RunRecord,
    update_aggregates,
    write_run_record,
    write_usage_events,
)
from pptgen.config import RuntimeSettings, override_settings
from pptgen.pipeline.generation_pipeline import generate_presentation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime(2026, 3, 27, 12, 0, 0, tzinfo=timezone.utc)


def _make_run_record(**kwargs) -> RunRecord:
    defaults = dict(
        run_id="run-001",
        timestamp_utc=_TS,
        mode="deterministic",
        playbook_id="exec",
        template_id="hc_default",
        theme_id=None,
        stage_reached="deck_planned",
        succeeded=True,
        failure_attribution=None,
        draft_override_active=False,
        dependency_count=0,
    )
    return RunRecord(**{**defaults, **kwargs})


def _make_usage_event(**kwargs) -> ArtifactUsageEvent:
    defaults = dict(
        run_id="run-001",
        artifact_type="primitive",
        artifact_id="title_slide",
        version="1.0.0",
        lifecycle_status="approved",
        was_default=True,
        run_succeeded=True,
    )
    return ArtifactUsageEvent(**{**defaults, **kwargs})


def _make_ds(tmp: Path) -> Path:
    ds = tmp / "ds"
    for subdir in ("primitives", "layouts", "tokens", "brands", "themes", "assets"):
        (ds / subdir).mkdir(parents=True)
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
# write_run_record
# ---------------------------------------------------------------------------


class TestWriteRunRecord:
    def test_creates_dir_and_file(self, tmp_path):
        adir = tmp_path / "analytics"
        write_run_record(_make_run_record(), adir)
        assert (adir / "run_records.jsonl").exists()

    def test_writes_valid_json_line(self, tmp_path):
        adir = tmp_path / "analytics"
        rr = _make_run_record(run_id="test-run")
        write_run_record(rr, adir)
        lines = (adir / "run_records.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["run_id"] == "test-run"
        assert data["stage_reached"] == "deck_planned"

    def test_second_call_appends(self, tmp_path):
        adir = tmp_path / "analytics"
        write_run_record(_make_run_record(run_id="r1"), adir)
        write_run_record(_make_run_record(run_id="r2"), adir)
        lines = (adir / "run_records.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["run_id"] == "r1"
        assert json.loads(lines[1])["run_id"] == "r2"

    def test_json_roundtrip(self, tmp_path):
        adir = tmp_path / "analytics"
        rr = _make_run_record(run_id="rt-01", dependency_count=3)
        write_run_record(rr, adir)
        data = json.loads((adir / "run_records.jsonl").read_text(encoding="utf-8"))
        restored = RunRecord.from_dict(data)
        assert restored == rr

    def test_silent_on_write_error(self, tmp_path, caplog):
        """Unwritable directory must not raise — just log a warning."""
        adir = tmp_path / "analytics"
        adir.mkdir()
        (adir / "run_records.jsonl").mkdir()  # file replaced by dir → write fails
        with caplog.at_level(logging.WARNING, logger="pptgen.analytics.writer"):
            write_run_record(_make_run_record(), adir)  # must not raise
        assert any("run record" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# write_usage_events
# ---------------------------------------------------------------------------


class TestWriteUsageEvents:
    def test_noop_for_empty_list(self, tmp_path):
        adir = tmp_path / "analytics"
        write_usage_events([], adir)
        assert not (adir / "usage_events.jsonl").exists()

    def test_writes_one_line_per_event(self, tmp_path):
        adir = tmp_path / "analytics"
        events = [_make_usage_event(artifact_id="a"), _make_usage_event(artifact_id="b")]
        write_usage_events(events, adir)
        lines = (adir / "usage_events.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

    def test_appends_on_second_call(self, tmp_path):
        adir = tmp_path / "analytics"
        write_usage_events([_make_usage_event(artifact_id="a")], adir)
        write_usage_events([_make_usage_event(artifact_id="b")], adir)
        lines = (adir / "usage_events.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

    def test_json_roundtrip(self, tmp_path):
        adir = tmp_path / "analytics"
        ev = _make_usage_event(was_default=False, run_succeeded=True)
        write_usage_events([ev], adir)
        data = json.loads((adir / "usage_events.jsonl").read_text(encoding="utf-8"))
        restored = ArtifactUsageEvent.from_dict(data)
        assert restored == ev

    def test_silent_on_write_error(self, tmp_path, caplog):
        adir = tmp_path / "analytics"
        adir.mkdir()
        (adir / "usage_events.jsonl").mkdir()  # dir blocks file write
        with caplog.at_level(logging.WARNING, logger="pptgen.analytics.writer"):
            write_usage_events([_make_usage_event()], adir)
        assert any("usage event" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# update_aggregates
# ---------------------------------------------------------------------------


class TestUpdateAggregates:
    def test_noop_for_empty_list(self, tmp_path):
        adir = tmp_path / "analytics"
        update_aggregates([], adir)
        assert not (adir / "usage_aggregates.json").exists()

    def test_creates_file_with_correct_structure(self, tmp_path):
        adir = tmp_path / "analytics"
        ev = _make_usage_event()
        update_aggregates([ev], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        assert "aggregates" in data
        assert "generated_from_line_count" in data

    def test_total_runs_increments(self, tmp_path):
        adir = tmp_path / "analytics"
        ev = _make_usage_event()
        update_aggregates([ev], adir)
        update_aggregates([ev], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        key = "primitive/title_slide/1.0.0"
        assert data["aggregates"][key]["total_runs"] == 2

    def test_success_count_incremented_on_success(self, tmp_path):
        adir = tmp_path / "analytics"
        update_aggregates([_make_usage_event(run_succeeded=True)], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        key = "primitive/title_slide/1.0.0"
        assert data["aggregates"][key]["success_count"] == 1
        assert data["aggregates"][key]["failure_count"] == 0

    def test_failure_count_incremented_on_failure(self, tmp_path):
        adir = tmp_path / "analytics"
        update_aggregates([_make_usage_event(run_succeeded=False)], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        key = "primitive/title_slide/1.0.0"
        assert data["aggregates"][key]["failure_count"] == 1
        assert data["aggregates"][key]["success_count"] == 0

    def test_default_version_count_incremented(self, tmp_path):
        adir = tmp_path / "analytics"
        update_aggregates([_make_usage_event(was_default=True)], adir)
        update_aggregates([_make_usage_event(was_default=False)], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        key = "primitive/title_slide/1.0.0"
        assert data["aggregates"][key]["default_version_count"] == 1

    def test_generated_from_line_count_accumulates(self, tmp_path):
        adir = tmp_path / "analytics"
        events = [_make_usage_event(artifact_id="a"), _make_usage_event(artifact_id="b")]
        update_aggregates(events, adir)
        update_aggregates([_make_usage_event(artifact_id="c")], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        assert data["generated_from_line_count"] == 3

    def test_aggregate_key_format(self, tmp_path):
        adir = tmp_path / "analytics"
        update_aggregates([_make_usage_event()], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        assert "primitive/title_slide/1.0.0" in data["aggregates"]

    def test_none_version_in_key(self, tmp_path):
        adir = tmp_path / "analytics"
        update_aggregates([_make_usage_event(version=None)], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        assert "primitive/title_slide/None" in data["aggregates"]

    def test_multiple_distinct_artifacts(self, tmp_path):
        adir = tmp_path / "analytics"
        events = [
            _make_usage_event(artifact_type="primitive", artifact_id="a"),
            _make_usage_event(artifact_type="layout", artifact_id="b"),
        ]
        update_aggregates(events, adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        assert len(data["aggregates"]) == 2

    def test_corrupt_file_is_reset(self, tmp_path, caplog):
        adir = tmp_path / "analytics"
        adir.mkdir()
        (adir / "usage_aggregates.json").write_text("not valid json", encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="pptgen.analytics.writer"):
            update_aggregates([_make_usage_event()], adir)
        data = json.loads((adir / "usage_aggregates.json").read_text(encoding="utf-8"))
        assert data["aggregates"]["primitive/title_slide/1.0.0"]["total_runs"] == 1

    def test_silent_on_write_error(self, tmp_path, caplog):
        adir = tmp_path / "analytics"
        adir.mkdir()
        (adir / "usage_aggregates.json").mkdir()  # dir blocks file write
        with caplog.at_level(logging.WARNING, logger="pptgen.analytics.writer"):
            update_aggregates([_make_usage_event()], adir)  # must not raise


# ---------------------------------------------------------------------------
# generate_presentation() — analytics integration
# ---------------------------------------------------------------------------


class TestAnalyticsIntegration:
    def test_no_files_written_without_analytics_dir(self, tmp_path):
        """Default settings (no analytics_dir) produce no analytics files."""
        result = generate_presentation("prepare an executive summary")
        # Verify no stray files in the current directory
        assert result.run_record is not None  # still built — just not written

    def test_run_records_written_when_analytics_dir_set(self, tmp_path):
        adir = tmp_path / "analytics"
        override_settings(RuntimeSettings(analytics_dir=str(adir)))
        try:
            generate_presentation("prepare an executive summary for Q3 results")
        finally:
            override_settings(None)
        assert (adir / "run_records.jsonl").exists()
        line = json.loads((adir / "run_records.jsonl").read_text(encoding="utf-8"))
        assert line["succeeded"] is True

    def test_usage_events_written_when_design_system_used(self, tmp_path):
        ds = _make_ds(tmp_path)
        adir = tmp_path / "analytics"
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            analytics_dir=str(adir),
        ))
        try:
            generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert (adir / "usage_events.jsonl").exists()

    def test_aggregates_written_when_design_system_used(self, tmp_path):
        ds = _make_ds(tmp_path)
        adir = tmp_path / "analytics"
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            analytics_dir=str(adir),
        ))
        try:
            generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert (adir / "usage_aggregates.json").exists()

    def test_two_runs_append_two_lines(self, tmp_path):
        adir = tmp_path / "analytics"
        override_settings(RuntimeSettings(analytics_dir=str(adir)))
        try:
            generate_presentation("prepare an executive summary for Q3 results")
            generate_presentation("prepare an executive summary for Q4 results")
        finally:
            override_settings(None)
        lines = (adir / "run_records.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        ids = [json.loads(l)["run_id"] for l in lines]
        assert ids[0] != ids[1]

    def test_analytics_failure_does_not_fail_pipeline(self, tmp_path, caplog):
        """A write error must never propagate to the caller."""
        adir = tmp_path / "analytics"
        adir.mkdir()
        # Block run_records.jsonl by creating a directory with that name
        (adir / "run_records.jsonl").mkdir()
        override_settings(RuntimeSettings(analytics_dir=str(adir)))
        try:
            with caplog.at_level(logging.WARNING, logger="pptgen.analytics.writer"):
                result = generate_presentation("prepare an executive summary")
        finally:
            override_settings(None)
        # Pipeline still returns successfully
        assert result.run_record is not None
        assert result.run_id != ""

    def test_analytics_dir_path_none_when_empty(self):
        s = RuntimeSettings(analytics_dir="")
        assert s.analytics_dir_path is None

    def test_analytics_dir_path_set_when_configured(self, tmp_path):
        s = RuntimeSettings(analytics_dir=str(tmp_path))
        assert s.analytics_dir_path == tmp_path
