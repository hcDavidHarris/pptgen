"""Tests for SQLiteRunStore."""
from __future__ import annotations

import pytest

from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def store(tmp_path):
    s = SQLiteRunStore(db_path=tmp_path / "artifacts.db")
    yield s
    s.close()


class TestCreateAndGet:
    def test_create_then_get(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        fetched = store.get(run.run_id)
        assert fetched.run_id == run.run_id
        assert fetched.status == RunStatus.RUNNING

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("nonexistent") is None

    def test_create_preserves_source(self, store):
        run = RunRecord.create(source=RunSource.API_ASYNC)
        store.create(run)
        assert store.get(run.run_id).source == RunSource.API_ASYNC

    def test_create_preserves_job_id(self, store):
        run = RunRecord.create(source=RunSource.API_ASYNC, job_id="job123")
        store.create(run)
        assert store.get(run.run_id).job_id == "job123"

    def test_create_preserves_template_id(self, store):
        run = RunRecord.create(source=RunSource.CLI, template_id="ops_review_v1")
        store.create(run)
        assert store.get(run.run_id).template_id == "ops_review_v1"

    def test_started_at_preserved(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        fetched = store.get(run.run_id)
        assert fetched.started_at is not None


class TestUpdateStatus:
    def test_update_to_succeeded(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED, total_ms=1234.5)
        updated = store.get(run.run_id)
        assert updated.status == RunStatus.SUCCEEDED
        assert updated.completed_at is not None
        assert updated.total_ms == pytest.approx(1234.5)

    def test_update_to_failed_stores_error(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(
            run.run_id, RunStatus.FAILED,
            error_category="validation", error_message="bad input",
        )
        updated = store.get(run.run_id)
        assert updated.status == RunStatus.FAILED
        assert updated.error_category == "validation"
        assert updated.error_message == "bad input"

    def test_update_manifest_path(self, store):
        run = RunRecord.create(source=RunSource.API_ASYNC)
        store.create(run)
        store.update_status(
            run.run_id, RunStatus.SUCCEEDED,
            manifest_path=f"runs/{run.run_id}/manifest.json",
        )
        assert "manifest.json" in store.get(run.run_id).manifest_path

    def test_update_playbook_id(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED, playbook_id="ops_review")
        assert store.get(run.run_id).playbook_id == "ops_review"

    def test_running_status_no_completed_at(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        # Update to non-terminal status
        store.update_status(run.run_id, RunStatus.RUNNING)
        assert store.get(run.run_id).completed_at is None

    def test_terminal_status_sets_completed_at(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED)
        assert store.get(run.run_id).completed_at is not None


class TestFromSettings:
    def test_from_settings(self, tmp_path):
        from pptgen.config import RuntimeSettings
        settings = RuntimeSettings(
            workspace_base=str(tmp_path / "ws"),
            artifact_db_path=str(tmp_path / "artifacts.db"),
        )
        store = SQLiteRunStore.from_settings(settings)
        try:
            run = RunRecord.create(source=RunSource.API_SYNC)
            store.create(run)
            assert store.get(run.run_id) is not None
        finally:
            store.close()
