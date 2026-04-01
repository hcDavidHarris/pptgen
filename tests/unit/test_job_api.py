"""API tests for /v1/jobs endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.jobs.models import JobRecord, JobStatus
from pptgen.jobs.sqlite_store import SQLiteJobStore


@pytest.fixture
def client_with_store(tmp_path: Path):
    """TestClient with injected temp job store and no background worker."""
    store = SQLiteJobStore(db_path=tmp_path / "test_jobs.db")
    app.state.job_store = store
    app.state.job_worker = None   # disable worker in tests
    # Use raise_server_exceptions=False so we can inspect error responses
    client = TestClient(app, raise_server_exceptions=False)
    yield client, store
    store.close()
    app.state.job_store = None


class TestSubmitJob:
    def test_submit_returns_202(self, client_with_store):
        client, _ = client_with_store
        resp = client.post("/v1/jobs", json={"input_text": "Meeting notes."})
        assert resp.status_code == 202

    def test_submit_response_has_job_id(self, client_with_store):
        client, _ = client_with_store
        resp = client.post("/v1/jobs", json={"input_text": "Meeting notes."})
        data = resp.json()
        assert "job_id" in data
        assert len(data["job_id"]) == 32

    def test_submit_response_has_run_id(self, client_with_store):
        client, _ = client_with_store
        resp = client.post("/v1/jobs", json={"input_text": "Meeting notes."})
        assert "run_id" in resp.json()

    def test_submit_status_is_queued(self, client_with_store):
        client, _ = client_with_store
        resp = client.post("/v1/jobs", json={"input_text": "Meeting notes."})
        assert resp.json()["status"] == "queued"

    def test_submit_stores_job_in_store(self, client_with_store):
        client, store = client_with_store
        resp = client.post("/v1/jobs", json={"input_text": "Meeting notes."})
        job_id = resp.json()["job_id"]
        assert store.get(job_id) is not None

    def test_submit_invalid_workload_type(self, client_with_store):
        client, _ = client_with_store
        resp = client.post("/v1/jobs", json={"input_text": "text", "workload_type": "invalid"})
        assert resp.status_code == 422

    def test_submit_batch_workload_type(self, client_with_store):
        client, _ = client_with_store
        resp = client.post("/v1/jobs", json={"input_text": "text", "workload_type": "batch"})
        assert resp.status_code == 202
        assert resp.json()["workload_type"] == "batch"

    def test_submit_with_template_id(self, client_with_store):
        client, store = client_with_store
        resp = client.post(
            "/v1/jobs",
            json={"input_text": "text", "template_id": "ops_review_v1"},
        )
        job_id = resp.json()["job_id"]
        assert store.get(job_id).template_id == "ops_review_v1"


class TestGetJobStatus:
    def test_get_existing_job(self, client_with_store):
        client, store = client_with_store
        job = JobRecord.create("test text")
        store.submit(job)
        resp = client.get(f"/v1/jobs/{job.job_id}")
        assert resp.status_code == 200
        assert resp.json()["job_id"] == job.job_id

    def test_get_returns_correct_status(self, client_with_store):
        client, store = client_with_store
        job = JobRecord.create("test text")
        store.submit(job)
        resp = client.get(f"/v1/jobs/{job.job_id}")
        assert resp.json()["status"] == "queued"

    def test_get_nonexistent_job_404(self, client_with_store):
        client, _ = client_with_store
        resp = client.get("/v1/jobs/nonexistent")
        assert resp.status_code == 404

    def test_get_reflects_status_update(self, client_with_store):
        client, store = client_with_store
        job = JobRecord.create("text")
        store.submit(job)
        store.update_status(job.job_id, JobStatus.SUCCEEDED, output_path="/tmp/out.pptx")
        resp = client.get(f"/v1/jobs/{job.job_id}")
        data = resp.json()
        assert data["status"] == "succeeded"
        assert data["output_path"] == "/tmp/out.pptx"


class TestCancelJob:
    def test_cancel_queued_job_returns_accepted_true(self, client_with_store):
        client, store = client_with_store
        job = JobRecord.create("text")
        store.submit(job)
        resp = client.post(f"/v1/jobs/{job.job_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["accepted"] is True
        assert resp.json()["status"] == "cancelled"

    def test_cancel_changes_status_to_cancelled(self, client_with_store):
        client, store = client_with_store
        job = JobRecord.create("text")
        store.submit(job)
        client.post(f"/v1/jobs/{job.job_id}/cancel")
        assert store.get(job.job_id).status == JobStatus.CANCELLED

    def test_cancel_running_job_returns_cancellation_requested(self, client_with_store):
        client, store = client_with_store
        job = JobRecord.create("text")
        store.submit(job)
        store.claim_next("test-worker")
        resp = client.post(f"/v1/jobs/{job.job_id}/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] is True
        assert data["status"] == "cancellation_requested"

    def test_cancel_nonexistent_job_404(self, client_with_store):
        client, _ = client_with_store
        resp = client.post("/v1/jobs/nonexistent/cancel")
        assert resp.status_code == 404
