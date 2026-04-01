"""Tests for GET /v1/system/health endpoint (PR 4 — System Health)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.jobs.models import JobRecord, JobStatus, WorkloadType
from pptgen.jobs.sqlite_store import SQLiteJobStore
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def client_with_stores(tmp_path):
    db = tmp_path / "artifacts.db"
    job_db = tmp_path / "jobs.db"
    run_store = SQLiteRunStore(db_path=db)
    job_store = SQLiteJobStore(db_path=job_db)
    app.state.run_store = run_store
    app.state.job_store = job_store
    client = TestClient(app, raise_server_exceptions=False)
    yield client, run_store, job_store
    run_store.close()
    job_store.close()
    app.state.run_store = None
    app.state.job_store = None


@pytest.fixture
def client_no_stores():
    app.state.run_store = None
    app.state.job_store = None
    client = TestClient(app, raise_server_exceptions=False)
    yield client


class TestSystemHealthEndpoint:
    def test_healthy_with_empty_stores(self, client_with_stores):
        client, _, _ = client_with_stores
        resp = client.get("/v1/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["run_store_ok"] is True
        assert data["job_store_ok"] is True

    def test_queued_jobs_count(self, client_with_stores):
        client, _, job_store = client_with_stores
        job = JobRecord.create(input_text="test", workload_type=WorkloadType.INTERACTIVE)
        job_store.submit(job)
        resp = client.get("/v1/system/health")
        data = resp.json()
        assert data["queued_jobs"] == 1
        assert data["running_jobs"] == 0

    def test_running_jobs_count(self, client_with_stores):
        client, _, job_store = client_with_stores
        job = JobRecord.create(input_text="test", workload_type=WorkloadType.INTERACTIVE)
        job_store.submit(job)
        job_store.claim_next(worker_id="w1")
        resp = client.get("/v1/system/health")
        data = resp.json()
        assert data["queued_jobs"] == 0
        assert data["running_jobs"] == 1

    def test_failed_jobs_1h_count(self, client_with_stores):
        client, _, job_store = client_with_stores
        job = JobRecord.create(input_text="test", workload_type=WorkloadType.INTERACTIVE)
        job_store.submit(job)
        job_store.update_status(job.job_id, JobStatus.FAILED, error_category="PipelineError")
        resp = client.get("/v1/system/health")
        data = resp.json()
        assert data["failed_jobs_1h"] == 1

    def test_zero_counts_when_empty(self, client_with_stores):
        client, _, _ = client_with_stores
        resp = client.get("/v1/system/health")
        data = resp.json()
        assert data["queued_jobs"] == 0
        assert data["running_jobs"] == 0
        assert data["failed_jobs_1h"] == 0

    def test_degraded_when_no_stores(self, client_no_stores):
        resp = client_no_stores.get("/v1/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["run_store_ok"] is False
        assert data["job_store_ok"] is False

    def test_response_shape(self, client_with_stores):
        client, _, _ = client_with_stores
        resp = client.get("/v1/system/health")
        data = resp.json()
        expected_keys = {
            "status", "queued_jobs", "running_jobs",
            "failed_jobs_1h", "run_store_ok", "job_store_ok",
        }
        assert expected_keys.issubset(data.keys())
