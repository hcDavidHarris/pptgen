"""Tests for GET /v1/jobs/{job_id}/runs endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.jobs.models import JobRecord
from pptgen.jobs.sqlite_store import SQLiteJobStore
from pptgen.runs.models import RunRecord, RunSource
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def client_with_stores(tmp_path):
    job_db = tmp_path / "jobs.db"
    artifact_db = tmp_path / "artifacts.db"
    job_store = SQLiteJobStore(db_path=job_db)
    run_store = SQLiteRunStore(db_path=artifact_db)
    artifact_store = SQLiteArtifactStore(db_path=artifact_db)
    artifact_storage = ArtifactStorage(base=tmp_path / "store")

    app.state.job_store = job_store
    app.state.run_store = run_store
    app.state.artifact_store = artifact_store
    app.state.artifact_storage = artifact_storage

    client = TestClient(app, raise_server_exceptions=False)
    yield client, job_store, run_store
    job_store.close()
    run_store.close()
    artifact_store.close()
    app.state.job_store = None
    app.state.run_store = None
    app.state.artifact_store = None
    app.state.artifact_storage = None


class TestJobRunsEndpoint:
    def test_unknown_job_404(self, client_with_stores):
        client, _, _ = client_with_stores
        resp = client.get("/v1/jobs/nonexistent/runs")
        assert resp.status_code == 404

    def test_job_with_no_runs_returns_empty(self, client_with_stores):
        client, job_store, _ = client_with_stores
        job = JobRecord.create("some text")
        job_store.submit(job)
        resp = client.get(f"/v1/jobs/{job.job_id}/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_job_with_runs_returns_them(self, client_with_stores):
        client, job_store, run_store = client_with_stores
        job = JobRecord.create("some text")
        job_store.submit(job)
        run = RunRecord.create(source=RunSource.API_ASYNC, job_id=job.job_id)
        run_store.create(run)
        resp = client.get(f"/v1/jobs/{job.job_id}/runs")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["job_id"] == job.job_id

    def test_runs_from_different_jobs_not_mixed(self, client_with_stores):
        client, job_store, run_store = client_with_stores
        job1 = JobRecord.create("text1")
        job2 = JobRecord.create("text2")
        job_store.submit(job1)
        job_store.submit(job2)
        run1 = RunRecord.create(source=RunSource.API_ASYNC, job_id=job1.job_id)
        run2 = RunRecord.create(source=RunSource.API_ASYNC, job_id=job2.job_id)
        run_store.create(run1)
        run_store.create(run2)

        resp = client.get(f"/v1/jobs/{job1.job_id}/runs")
        items = resp.json()
        assert len(items) == 1
        assert items[0]["job_id"] == job1.job_id
