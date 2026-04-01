"""Tests for POST /v1/runs/{run_id}/rerun."""
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


def make_run(run_store, status=RunStatus.SUCCEEDED, input_text="Hello world") -> RunRecord:
    run = RunRecord.create(source=RunSource.API_SYNC, input_text=input_text)
    run_store.create(run)
    run_store.update_status(run.run_id, status)
    return run_store.get(run.run_id)


class TestRerunRun:
    def test_rerun_succeeded_run(self, stores):
        client, run_store, _ = stores
        run = make_run(run_store, RunStatus.SUCCEEDED)
        resp = client.post(f"/v1/runs/{run.run_id}/rerun")
        assert resp.status_code == 200

    def test_rerun_failed_run(self, stores):
        client, run_store, _ = stores
        run = make_run(run_store, RunStatus.FAILED)
        resp = client.post(f"/v1/runs/{run.run_id}/rerun")
        assert resp.status_code == 200

    def test_rerun_any_status_allowed(self, stores):
        client, run_store, _ = stores
        run = RunRecord.create(source=RunSource.API_SYNC, input_text="test")
        run_store.create(run)
        # Running status should still be allowed for rerun
        resp = client.post(f"/v1/runs/{run.run_id}/rerun")
        assert resp.status_code == 200

    def test_rerun_creates_new_run_with_lineage(self, stores):
        client, run_store, _ = stores
        run = make_run(run_store)
        resp = client.post(f"/v1/runs/{run.run_id}/rerun")
        data = resp.json()
        assert data["action_type"] == "rerun"
        assert data["source_run_id"] == run.run_id
        assert data["run_id"] != run.run_id

    def test_rerun_creates_job(self, stores):
        client, run_store, job_store = stores
        run = make_run(run_store)
        resp = client.post(f"/v1/runs/{run.run_id}/rerun")
        data = resp.json()
        assert data["job_id"] is not None
        job = job_store.get(data["job_id"])
        assert job is not None
        assert job.action_type == "rerun"

    def test_rerun_not_found_returns_404(self, stores):
        client, _, _ = stores
        resp = client.post("/v1/runs/nonexistent/rerun")
        assert resp.status_code == 404

    def test_rerun_no_input_text_returns_422(self, stores):
        client, run_store, _ = stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        resp = client.post(f"/v1/runs/{run.run_id}/rerun")
        assert resp.status_code == 422

    def test_rerun_new_run_preserves_input(self, stores):
        client, run_store, _ = stores
        run = make_run(run_store, input_text="Specific meeting notes")
        resp = client.post(f"/v1/runs/{run.run_id}/rerun")
        new_run = run_store.get(resp.json()["run_id"])
        assert new_run.input_text == "Specific meeting notes"
