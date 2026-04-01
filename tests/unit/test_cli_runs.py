"""Tests for pptgen runs CLI commands."""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from pptgen.cli import app
from pptgen.config.settings import RuntimeSettings, override_settings
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore

runner = CliRunner()


@pytest.fixture
def db_with_store(tmp_path):
    db = tmp_path / "artifacts.db"
    store = SQLiteRunStore(db_path=db)
    settings = RuntimeSettings(artifact_db_path=str(db))
    override_settings(settings)
    yield store, tmp_path
    store.close()
    override_settings(None)


class TestRunsList:
    def test_list_empty(self, db_with_store):
        result = runner.invoke(app, ["runs", "list"])
        assert result.exit_code == 0
        assert "No runs found" in result.output

    def test_list_shows_run(self, db_with_store):
        store, _ = db_with_store
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED, total_ms=250.0)
        result = runner.invoke(app, ["runs", "list"])
        assert result.exit_code == 0
        assert run.run_id in result.output
        assert "succeeded" in result.output

    def test_list_json_output(self, db_with_store):
        store, _ = db_with_store
        run = RunRecord.create(source=RunSource.CLI)
        store.create(run)
        result = runner.invoke(app, ["runs", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["run_id"] == run.run_id

    def test_list_filter_by_status(self, db_with_store):
        store, _ = db_with_store
        r1 = RunRecord.create(source=RunSource.API_SYNC)
        store.create(r1)
        store.update_status(r1.run_id, RunStatus.SUCCEEDED)
        r2 = RunRecord.create(source=RunSource.API_SYNC)
        store.create(r2)
        store.update_status(r2.run_id, RunStatus.FAILED)
        result = runner.invoke(app, ["runs", "list", "--status", "succeeded", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["status"] == "succeeded"


class TestRunsShow:
    def test_show_existing_run(self, db_with_store):
        store, _ = db_with_store
        run = RunRecord.create(source=RunSource.API_ASYNC)
        store.create(run)
        result = runner.invoke(app, ["runs", "show", run.run_id])
        assert result.exit_code == 0
        assert run.run_id in result.output
        assert "api_async" in result.output

    def test_show_nonexistent_exits_1(self, db_with_store):
        result = runner.invoke(app, ["runs", "show", "nonexistent"])
        assert result.exit_code == 1

    def test_show_json_output(self, db_with_store):
        store, _ = db_with_store
        run = RunRecord.create(source=RunSource.CLI)
        store.create(run)
        result = runner.invoke(app, ["runs", "show", run.run_id, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["run_id"] == run.run_id
        assert data["source"] == "cli"

    def test_show_json_has_artifact_count(self, db_with_store):
        store, _ = db_with_store
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED, artifact_count=3)
        result = runner.invoke(app, ["runs", "show", run.run_id, "--json"])
        data = json.loads(result.output)
        assert data["artifact_count"] == 3


class TestRunsMetrics:
    def test_metrics_no_timings(self, db_with_store):
        store, _ = db_with_store
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        result = runner.invoke(app, ["runs", "metrics", run.run_id])
        assert result.exit_code == 0
        assert "No stage timings recorded" in result.output

    def test_metrics_with_timings(self, db_with_store):
        store, _ = db_with_store
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        timings = [{"stage": "planning", "duration_ms": 120.0}, {"stage": "rendering", "duration_ms": 400.0}]
        store.update_status(run.run_id, RunStatus.SUCCEEDED, stage_timings=timings)
        result = runner.invoke(app, ["runs", "metrics", run.run_id])
        assert result.exit_code == 0
        assert "planning" in result.output
        assert "rendering" in result.output

    def test_metrics_json_output(self, db_with_store):
        store, _ = db_with_store
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        timings = [{"stage": "spec", "duration_ms": 50.0}]
        store.update_status(run.run_id, RunStatus.SUCCEEDED, stage_timings=timings, total_ms=50.0)
        result = runner.invoke(app, ["runs", "metrics", run.run_id, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["run_id"] == run.run_id
        assert len(data["stage_timings"]) == 1
        assert data["total_ms"] == 50.0

    def test_metrics_nonexistent_exits_1(self, db_with_store):
        result = runner.invoke(app, ["runs", "metrics", "notarun"])
        assert result.exit_code == 1
