"""Tests for run domain models."""
from __future__ import annotations

import pytest

from pptgen.runs.models import RunRecord, RunSource, RunStatus


class TestRunRecord:
    def test_create_returns_running_status(self):
        run = RunRecord.create(source=RunSource.API_SYNC)
        assert run.status == RunStatus.RUNNING

    def test_create_generates_run_id(self):
        run = RunRecord.create(source=RunSource.API_SYNC)
        assert len(run.run_id) == 32

    def test_create_unique_run_ids(self):
        r1 = RunRecord.create(source=RunSource.API_SYNC)
        r2 = RunRecord.create(source=RunSource.API_SYNC)
        assert r1.run_id != r2.run_id

    def test_create_sets_source(self):
        run = RunRecord.create(source=RunSource.CLI)
        assert run.source == RunSource.CLI

    def test_is_terminal_running_false(self):
        run = RunRecord.create(source=RunSource.API_SYNC)
        assert run.is_terminal() is False

    def test_is_terminal_succeeded_true(self):
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.SUCCEEDED
        assert run.is_terminal() is True

    def test_is_terminal_failed_true(self):
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.FAILED
        assert run.is_terminal() is True

    def test_is_terminal_cancelled_true(self):
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.CANCELLED
        assert run.is_terminal() is True

    def test_create_with_job_id(self):
        run = RunRecord.create(source=RunSource.API_ASYNC, job_id="abc123")
        assert run.job_id == "abc123"

    def test_create_template_id(self):
        run = RunRecord.create(source=RunSource.CLI, template_id="ops_review_v1")
        assert run.template_id == "ops_review_v1"

    def test_create_with_explicit_run_id(self):
        run = RunRecord.create(source=RunSource.API_ASYNC, run_id="myrunid12345678901234567890ab")
        assert run.run_id == "myrunid12345678901234567890ab"

    def test_create_defaults(self):
        run = RunRecord.create(source=RunSource.API_SYNC)
        assert run.mode == "deterministic"
        assert run.profile == "dev"
        assert run.job_id is None
        assert run.completed_at is None
        assert run.manifest_path is None
