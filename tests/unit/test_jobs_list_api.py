"""Tests for GET /v1/jobs list endpoint."""
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


def make_job(job_store, status=JobStatus.QUEUED, input_text="test") -> JobRecord:
    job = JobRecord.create(input_text=input_text)
    job_store.submit(job)
    if status != JobStatus.QUEUED:
        job_store.update_status(job.job_id, status)
    return job_store.get(job.job_id)


class TestListJobs:
    def test_list_jobs_empty(self, stores):
        client, _ = stores
        resp = client.get("/v1/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["jobs"] == []
        assert data["total"] == 0

    def test_list_jobs_returns_jobs(self, stores):
        client, job_store = stores
        make_job(job_store)
        make_job(job_store)
        resp = client.get("/v1/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["jobs"]) == 2
        assert data["total"] == 2

    def test_list_jobs_filter_by_status(self, stores):
        client, job_store = stores
        make_job(job_store, JobStatus.QUEUED)
        make_job(job_store, JobStatus.SUCCEEDED)
        make_job(job_store, JobStatus.FAILED)
        resp = client.get("/v1/jobs?status=succeeded")
        data = resp.json()
        assert data["total"] == 1
        assert data["jobs"][0]["status"] == "succeeded"

    def test_list_jobs_pagination(self, stores):
        client, job_store = stores
        for _ in range(5):
            make_job(job_store)
        resp = client.get("/v1/jobs?limit=2&offset=0")
        data = resp.json()
        assert len(data["jobs"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_list_jobs_response_has_action_type(self, stores):
        client, job_store = stores
        job = JobRecord.create(input_text="test", action_type="retry", source_run_id="abc")
        job_store.submit(job)
        resp = client.get("/v1/jobs")
        j = resp.json()["jobs"][0]
        assert j["action_type"] == "retry"
        assert j["source_run_id"] == "abc"

    def test_list_jobs_no_store_returns_503(self, tmp_path):
        old = getattr(app.state, "job_store", None)
        app.state.job_store = None
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/jobs")
        assert resp.status_code == 503
        app.state.job_store = old

    def test_list_jobs_ordered_newest_first(self, stores):
        import time
        client, job_store = stores
        j1 = make_job(job_store, input_text="first")
        time.sleep(0.01)
        j2 = make_job(job_store, input_text="second")
        resp = client.get("/v1/jobs")
        ids = [j["job_id"] for j in resp.json()["jobs"]]
        assert ids[0] == j2.job_id
        assert ids[1] == j1.job_id
