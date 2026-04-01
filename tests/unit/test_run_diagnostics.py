"""Tests for retry_count in RunResponse (PR 1 — Run Diagnostics backend)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.jobs.models import JobRecord, JobStatus, WorkloadType
from pptgen.jobs.sqlite_store import SQLiteJobStore
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def client_with_stores(tmp_path):
    db = tmp_path / "artifacts.db"
    jobs_db = tmp_path / "jobs.db"
    run_store = SQLiteRunStore(db_path=db)
    job_store = SQLiteJobStore(db_path=jobs_db)

    app.state.run_store = run_store
    app.state.job_store = job_store

    client = TestClient(app, raise_server_exceptions=False)
    yield client, run_store, job_store

    run_store.close()
    job_store.close()
    app.state.run_store = None
    app.state.job_store = None


class TestRunResponseRetryCount:
    def test_sync_run_has_no_retry_count(self, client_with_stores):
        """Sync runs have no job_id so retry_count must be None."""
        client, run_store, _ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        resp = client.get(f"/v1/runs/{run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["retry_count"] is None

    def test_async_run_has_retry_count_from_job(self, client_with_stores):
        """Async run with job_id must expose job's retry_count."""
        client, run_store, job_store = client_with_stores
        job = JobRecord.create(input_text="hello world")
        job_store.submit(job)
        # Simulate a retry
        job_store.update_status(
            job.job_id,
            JobStatus.RETRYING,
            retry_count=2,
        )
        run = RunRecord.create(source=RunSource.API_ASYNC)
        object.__setattr__(run, "job_id", job.job_id)
        run_store.create(run)
        resp = client.get(f"/v1/runs/{run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["retry_count"] == 2

    def test_retry_count_field_always_present(self, client_with_stores):
        """retry_count key must be present even when None."""
        client, run_store, _ = client_with_stores
        run = RunRecord.create(source=RunSource.CLI)
        run_store.create(run)
        resp = client.get(f"/v1/runs/{run.run_id}")
        assert resp.status_code == 200
        assert "retry_count" in resp.json()

    def test_run_not_found_returns_404(self, client_with_stores):
        client, _, _ = client_with_stores
        resp = client.get("/v1/runs/nonexistent-run-xyz")
        assert resp.status_code == 404
