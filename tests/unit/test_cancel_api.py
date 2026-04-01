"""Tests for POST /v1/jobs/{job_id}/cancel with new response schema."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.jobs.models import JobRecord, JobStatus
from pptgen.jobs.sqlite_store import SQLiteJobStore


@pytest.fixture
def stores(tmp_path):
    job_db = tmp_path / "jobs.db"
    job_store = SQLiteJobStore(db_path=job_db)
    app.state.job_store = job_store
    client = TestClient(app, raise_server_exceptions=False)
    yield client, job_store
    job_store.close()
    app.state.job_store = None


def make_job(job_store, status=JobStatus.QUEUED) -> JobRecord:
    job = JobRecord.create(input_text="test")
    job_store.submit(job)
    if status != JobStatus.QUEUED:
        job_store.update_status(job.job_id, status)
    return job_store.get(job.job_id)


class TestCancelJob:
    def test_cancel_queued_job(self, stores):
        client, job_store = stores
        job = make_job(job_store, JobStatus.QUEUED)
        resp = client.post(f"/v1/jobs/{job.job_id}/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] is True
        assert data["status"] == "cancelled"

    def test_cancel_retrying_job(self, stores):
        client, job_store = stores
        job = make_job(job_store, JobStatus.RETRYING)
        resp = client.post(f"/v1/jobs/{job.job_id}/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] is True
        assert data["status"] == "cancelled"

    def test_cancel_running_job_returns_cancellation_requested(self, stores):
        client, job_store = stores
        job = make_job(job_store, JobStatus.RUNNING)
        resp = client.post(f"/v1/jobs/{job.job_id}/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] is True
        assert data["status"] == "cancellation_requested"

    def test_cancel_terminal_job_not_accepted(self, stores):
        client, job_store = stores
        job = make_job(job_store, JobStatus.SUCCEEDED)
        resp = client.post(f"/v1/jobs/{job.job_id}/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] is False

    def test_cancel_not_found(self, stores):
        client, _ = stores
        resp = client.post("/v1/jobs/nonexistent/cancel")
        assert resp.status_code == 404

    def test_cancel_persists_status(self, stores):
        client, job_store = stores
        job = make_job(job_store, JobStatus.QUEUED)
        client.post(f"/v1/jobs/{job.job_id}/cancel")
        updated = job_store.get(job.job_id)
        assert updated.status == JobStatus.CANCELLED

    def test_cancel_running_persists_cancellation_requested(self, stores):
        client, job_store = stores
        job = make_job(job_store, JobStatus.RUNNING)
        client.post(f"/v1/jobs/{job.job_id}/cancel")
        updated = job_store.get(job.job_id)
        assert updated.status == JobStatus.CANCELLATION_REQUESTED
