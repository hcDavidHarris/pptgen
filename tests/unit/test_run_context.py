"""Tests for RunContext and StageTimer (Stage 6A — PR 3)."""

from __future__ import annotations

import json
import time

import pytest

from pptgen.runtime import RunContext, StageTimer


# ---------------------------------------------------------------------------
# RunContext construction
# ---------------------------------------------------------------------------

class TestRunContextConstruction:
    def test_run_id_auto_generated(self):
        ctx = RunContext()
        assert ctx.run_id
        assert len(ctx.run_id) == 32   # uuid4().hex is 32 hex chars

    def test_run_ids_are_unique(self):
        ids = {RunContext().run_id for _ in range(20)}
        assert len(ids) == 20

    def test_request_id_defaults_to_none(self):
        assert RunContext().request_id is None

    def test_profile_defaults_to_dev(self):
        assert RunContext().profile == "dev"

    def test_mode_defaults_to_deterministic(self):
        assert RunContext().mode == "deterministic"

    def test_playbook_id_defaults_to_none(self):
        assert RunContext().playbook_id is None

    def test_template_id_defaults_to_none(self):
        assert RunContext().template_id is None

    def test_workspace_path_defaults_to_none(self):
        assert RunContext().workspace_path is None

    def test_config_fingerprint_defaults_to_none(self):
        assert RunContext().config_fingerprint is None

    def test_timings_starts_empty(self):
        assert RunContext().timings == []

    def test_started_at_is_utc(self):
        import datetime
        ctx = RunContext()
        assert ctx.started_at.tzinfo is not None
        assert ctx.started_at.tzinfo == datetime.timezone.utc

    def test_fields_assignable(self):
        ctx = RunContext()
        ctx.playbook_id = "meeting-notes-to-eos-rocks"
        ctx.request_id = "req-abc"
        ctx.workspace_path = "/tmp/pptgen_api/abc123"
        assert ctx.playbook_id == "meeting-notes-to-eos-rocks"
        assert ctx.request_id == "req-abc"
        assert ctx.workspace_path == "/tmp/pptgen_api/abc123"


# ---------------------------------------------------------------------------
# Stage timing
# ---------------------------------------------------------------------------

class TestStageTimer:
    def test_duration_ms_none_when_not_ended(self):
        t = StageTimer(stage="test", started_at=time.monotonic())
        assert t.duration_ms is None

    def test_duration_ms_positive_after_end(self):
        t = StageTimer(stage="test", started_at=time.monotonic())
        time.sleep(0.01)
        t.ended_at = time.monotonic()
        assert t.duration_ms is not None
        assert t.duration_ms >= 10  # at least 10 ms

    def test_duration_ms_computation(self):
        t = StageTimer(stage="test", started_at=0.0, ended_at=0.5)
        assert t.duration_ms == pytest.approx(500.0)


class TestRunContextStaging:
    def test_start_creates_timer(self):
        ctx = RunContext()
        ctx.start_stage("route_input")
        assert len(ctx.timings) == 1
        assert ctx.timings[0].stage == "route_input"
        assert ctx.timings[0].ended_at is None

    def test_end_sets_ended_at(self):
        ctx = RunContext()
        ctx.start_stage("route_input")
        ctx.end_stage("route_input")
        assert ctx.timings[0].ended_at is not None

    def test_duration_ms_positive_after_start_end(self):
        ctx = RunContext()
        ctx.start_stage("route_input")
        time.sleep(0.01)
        ctx.end_stage("route_input")
        assert ctx.timings[0].duration_ms is not None
        assert ctx.timings[0].duration_ms >= 0

    def test_multiple_stages_recorded(self):
        ctx = RunContext()
        for stage in ("route_input", "execute_playbook", "plan_slides", "render"):
            ctx.start_stage(stage)
            ctx.end_stage(stage)
        stages = [t.stage for t in ctx.timings]
        assert stages == ["route_input", "execute_playbook", "plan_slides", "render"]

    def test_end_stage_with_no_matching_start_is_noop(self):
        ctx = RunContext()
        ctx.end_stage("nonexistent")  # should not raise
        assert ctx.timings == []

    def test_end_stage_targets_most_recent_unfinished(self):
        ctx = RunContext()
        ctx.start_stage("route_input")
        ctx.end_stage("route_input")
        first_end = ctx.timings[0].ended_at

        ctx.start_stage("route_input")   # second timer for same stage
        time.sleep(0.001)
        ctx.end_stage("route_input")
        second_end = ctx.timings[1].ended_at

        assert ctx.timings[0].ended_at == first_end
        assert second_end is not None
        assert second_end > first_end  # type: ignore[operator]

    def test_total_ms_zero_when_no_timings(self):
        ctx = RunContext()
        assert ctx.total_ms() == 0.0

    def test_total_ms_positive_after_stages(self):
        ctx = RunContext()
        ctx.start_stage("a")
        time.sleep(0.01)
        ctx.end_stage("a")
        ctx.start_stage("b")
        time.sleep(0.01)
        ctx.end_stage("b")
        assert ctx.total_ms() >= 20  # at least 20 ms total

    def test_total_ms_covers_span_of_all_stages(self):
        ctx = RunContext()
        ctx.start_stage("early")
        time.sleep(0.005)
        ctx.start_stage("late")
        ctx.end_stage("early")
        time.sleep(0.005)
        ctx.end_stage("late")
        # total should be >= sum of individual durations
        sum_of_parts = sum(
            t.duration_ms for t in ctx.timings if t.duration_ms is not None
        )
        assert ctx.total_ms() >= sum_of_parts * 0.9  # allow small float tolerance


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestRunContextAsDict:
    def test_as_dict_contains_run_id(self):
        ctx = RunContext()
        d = ctx.as_dict()
        assert d["run_id"] == ctx.run_id

    def test_as_dict_contains_all_expected_keys(self):
        ctx = RunContext()
        d = ctx.as_dict()
        expected_keys = {
            "run_id", "request_id", "profile", "mode",
            "template_id", "playbook_id", "started_at",
            "timings", "total_ms", "config_fingerprint", "workspace_path",
        }
        assert set(d.keys()) >= expected_keys

    def test_as_dict_is_json_serializable(self):
        ctx = RunContext(
            request_id="req-001",
            profile="dev",
            mode="deterministic",
            config_fingerprint="abc12345",
        )
        ctx.start_stage("render")
        ctx.end_stage("render")
        serialized = json.dumps(ctx.as_dict())   # raises if not serializable
        assert serialized

    def test_as_dict_started_at_is_iso_string(self):
        ctx = RunContext()
        d = ctx.as_dict()
        assert isinstance(d["started_at"], str)
        assert "T" in d["started_at"]

    def test_as_dict_timings_list(self):
        ctx = RunContext()
        ctx.start_stage("render")
        ctx.end_stage("render")
        d = ctx.as_dict()
        assert isinstance(d["timings"], list)
        assert len(d["timings"]) == 1
        assert d["timings"][0]["stage"] == "render"
        assert d["timings"][0]["duration_ms"] is not None

    def test_as_dict_config_fingerprint_stored(self):
        ctx = RunContext(config_fingerprint="deadbeef")
        assert ctx.as_dict()["config_fingerprint"] == "deadbeef"

    def test_as_dict_workspace_path_stored(self):
        ctx = RunContext(workspace_path="/tmp/pptgen_api/abc")
        assert ctx.as_dict()["workspace_path"] == "/tmp/pptgen_api/abc"
