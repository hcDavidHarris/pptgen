"""Tests for POST /v1/runs/{run_id}/retry."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.jobs.sqlite_store import SQLiteJobStore
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def stores(tmp_path):
    db = tmp_path / "artifacts.db"
    job_db = tmp_path / "jobs.db"
    run_store = SQLiteRunStore(db_path=db)
    artifact_store = SQLiteArtifactStore(db_path=db)
    artifact_storage = ArtifactStorage(base=tmp_path / "store")
    job_store = SQLiteJobStore(db_path=job_db)

    app.state.run_store = run_store
    app.state.artifact_store = artifact_store
    app.state.artifact_storage = artifact_storage
    app.state.job_store = job_store

    client = TestClient(app, raise_server_exceptions=False)
    yield client, run_store, job_store
    run_store.close()
    artifact_store.close()
    job_store.close()
    app.state.run_store = None
    app.state.artifact_store = None
    app.state.artifact_storage = None
    app.state.job_store = None


def make_failed_run(run_store, input_text="Hello world") -> RunRecord:
    run = RunRecord.create(source=RunSource.API_SYNC, input_text=input_text)
    run_store.create(run)
    run_store.update_status(run.run_id, RunStatus.FAILED, error_category="system")
    return run_store.get(run.run_id)


class TestRetryRun:
    def test_retry_failed_run_returns_201(self, stores):
        client, run_store, _ = stores
        run = make_failed_run(run_store)
        resp = client.post(f"/v1/runs/{run.run_id}/retry")
        assert resp.status_code == 200

    def test_retry_creates_new_run(self, stores):
        client, run_store, _ = stores
        run = make_failed_run(run_store)
        resp = client.post(f"/v1/runs/{run.run_id}/retry")
        data = resp.json()
        assert data["run_id"] != run.run_id
        assert data["source_run_id"] == run.run_id
        assert data["action_type"] == "retry"

    def test_retry_creates_job(self, stores):
        client, run_store, job_store = stores
        run = make_failed_run(run_store)
        resp = client.post(f"/v1/runs/{run.run_id}/retry")
        data = resp.json()
        assert data["job_id"] is not None
        job = job_store.get(data["job_id"])
        assert job is not None
        assert job.action_type == "retry"
        assert job.source_run_id == run.run_id

    def test_retry_new_run_has_lineage(self, stores):
        client, run_store, _ = stores
        run = make_failed_run(run_store)
        resp = client.post(f"/v1/runs/{run.run_id}/retry")
        new_run = run_store.get(resp.json()["run_id"])
        assert new_run.action_type == "retry"
        assert new_run.source_run_id == run.run_id
        assert new_run.input_text == "Hello world"

    def test_retry_not_found_returns_404(self, stores):
        client, _, _ = stores
        resp = client.post("/v1/runs/nonexistent/retry")
        assert resp.status_code == 404

    def test_retry_non_failed_returns_409(self, stores):
        client, run_store, _ = stores
        run = RunRecord.create(source=RunSource.API_SYNC, input_text="test")
        run_store.create(run)
        # status is RUNNING (default)
        resp = client.post(f"/v1/runs/{run.run_id}/retry")
        assert resp.status_code == 409

    def test_retry_succeeded_returns_409(self, stores):
        client, run_store, _ = stores
        run = RunRecord.create(source=RunSource.API_SYNC, input_text="test")
        run_store.create(run)
        run_store.update_status(run.run_id, RunStatus.SUCCEEDED)
        resp = client.post(f"/v1/runs/{run.run_id}/retry")
        assert resp.status_code == 409

    def test_retry_no_input_text_returns_422(self, stores):
        client, run_store, _ = stores
        # Create failed run with NO input_text and no job linkage
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        run_store.update_status(run.run_id, RunStatus.FAILED)
        resp = client.post(f"/v1/runs/{run.run_id}/retry")
        assert resp.status_code == 422

    def test_get_run_includes_replay_available_true(self, stores):
        client, run_store, _ = stores
        run = make_failed_run(run_store)
        resp = client.get(f"/v1/runs/{run.run_id}")
        assert resp.json()["replay_available"] is True

    def test_get_run_replay_available_false_no_input(self, stores):
        client, run_store, _ = stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        resp = client.get(f"/v1/runs/{run.run_id}")
        assert resp.json()["replay_available"] is False
