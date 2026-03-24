"""Tests for CLI job commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pptgen.cli import app
from pptgen.config import RuntimeSettings, override_settings


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def input_file(tmp_path: Path) -> Path:
    f = tmp_path / "input.txt"
    f.write_text(
        "Meeting notes. Attendees: Alice. Action items and follow-up decisions.",
        encoding="utf-8",
    )
    return f


@pytest.fixture
def settings_with_db(tmp_path: Path):
    settings = RuntimeSettings(
        workspace_base=str(tmp_path / "ws"),
        job_db_path=str(tmp_path / "jobs.db"),
    )
    override_settings(settings)
    yield settings
    override_settings(None)


class TestJobSubmitCommand:
    def test_submit_prints_job_id(self, runner, input_file, settings_with_db):
        result = runner.invoke(app, ["job", "submit", str(input_file)])
        assert result.exit_code == 0
        assert "Submitted job:" in result.output

    def test_submit_prints_status(self, runner, input_file, settings_with_db):
        result = runner.invoke(app, ["job", "submit", str(input_file)])
        assert result.exit_code == 0
        assert "Status:" in result.output

    def test_submit_missing_file_exits_1(self, runner, settings_with_db):
        result = runner.invoke(app, ["job", "submit", "nonexistent.txt"])
        assert result.exit_code == 1

    def test_submit_creates_job_in_db(self, runner, input_file, settings_with_db):
        from pptgen.jobs.sqlite_store import SQLiteJobStore
        result = runner.invoke(app, ["job", "submit", str(input_file)])
        assert result.exit_code == 0
        job_id = result.output.split("Submitted job:")[1].split("\n")[0].strip()
        store = SQLiteJobStore.from_settings(settings_with_db)
        try:
            job = store.get(job_id)
            assert job is not None
        finally:
            store.close()

    def test_submit_batch_flag(self, runner, input_file, settings_with_db):
        from pptgen.jobs.models import WorkloadType
        from pptgen.jobs.sqlite_store import SQLiteJobStore
        result = runner.invoke(app, ["job", "submit", str(input_file), "--batch"])
        assert result.exit_code == 0
        job_id = result.output.split("Submitted job:")[1].split("\n")[0].strip()
        store = SQLiteJobStore.from_settings(settings_with_db)
        try:
            job = store.get(job_id)
            assert job.workload_type == WorkloadType.BATCH
        finally:
            store.close()


class TestJobStatusCommand:
    def test_status_nonexistent_job_exits_1(self, runner, settings_with_db):
        result = runner.invoke(app, ["job", "status", "nonexistent"])
        assert result.exit_code == 1

    def test_status_after_submit(self, runner, input_file, settings_with_db):
        # Submit first
        submit_result = runner.invoke(app, ["job", "submit", str(input_file)])
        assert submit_result.exit_code == 0
        job_id = submit_result.output.split("Submitted job:")[1].split("\n")[0].strip()

        # Then check status
        status_result = runner.invoke(app, ["job", "status", job_id])
        assert status_result.exit_code == 0
        assert job_id in status_result.output

    def test_status_shows_job_id(self, runner, input_file, settings_with_db):
        submit_result = runner.invoke(app, ["job", "submit", str(input_file)])
        job_id = submit_result.output.split("Submitted job:")[1].split("\n")[0].strip()

        status_result = runner.invoke(app, ["job", "status", job_id])
        assert "Job:" in status_result.output

    def test_status_json_output(self, runner, input_file, settings_with_db):
        submit_result = runner.invoke(app, ["job", "submit", str(input_file)])
        job_id = submit_result.output.split("Submitted job:")[1].split("\n")[0].strip()

        status_result = runner.invoke(app, ["job", "status", job_id, "--json"])
        assert status_result.exit_code == 0
        data = json.loads(status_result.output)
        assert data["job_id"] == job_id
        assert "status" in data

    def test_status_json_has_all_expected_fields(self, runner, input_file, settings_with_db):
        submit_result = runner.invoke(app, ["job", "submit", str(input_file)])
        job_id = submit_result.output.split("Submitted job:")[1].split("\n")[0].strip()

        status_result = runner.invoke(app, ["job", "status", job_id, "--json"])
        data = json.loads(status_result.output)
        for field in ("job_id", "status", "retry_count", "error_category",
                      "error_message", "output_path", "playbook_id"):
            assert field in data
