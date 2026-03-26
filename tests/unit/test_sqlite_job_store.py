"""Tests for SQLiteJobStore."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from pptgen.jobs.models import JobRecord, JobStatus, WorkloadType
from pptgen.jobs.sqlite_store import SQLiteJobStore


@pytest.fixture
def store(tmp_path: Path) -> SQLiteJobStore:
    s = SQLiteJobStore(db_path=tmp_path / "test_jobs.db")
    yield s
    s.close()


class TestSubmitAndGet:
    def test_submit_then_get(self, store):
        job = JobRecord.create("test input")
        store.submit(job)
        fetched = store.get(job.job_id)
        assert fetched is not None
        assert fetched.job_id == job.job_id
        assert fetched.status == JobStatus.QUEUED

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("nonexistent") is None

    def test_submit_preserves_workload_type(self, store):
        job = JobRecord.create("text", workload_type=WorkloadType.BATCH)
        store.submit(job)
        assert store.get(job.job_id).workload_type == WorkloadType.BATCH

    def test_submit_preserves_template_id(self, store):
        job = JobRecord.create("text", template_id="ops_review_v1")
        store.submit(job)
        assert store.get(job.job_id).template_id == "ops_review_v1"

    def test_submit_preserves_mode(self, store):
        job = JobRecord.create("text", mode="ai")
        store.submit(job)
        assert store.get(job.job_id).mode == "ai"


class TestClaimNext:
    def test_claim_returns_queued_job(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        claimed = store.claim_next("worker-1")
        assert claimed is not None
        assert claimed.job_id == job.job_id
        assert claimed.status == JobStatus.RUNNING

    def test_claim_empty_store_returns_none(self, store):
        assert store.claim_next("worker-1") is None

    def test_claim_sets_worker_id(self, store):
        store.submit(JobRecord.create("text"))
        claimed = store.claim_next("worker-42")
        assert claimed.worker_id == "worker-42"

    def test_claim_sets_claimed_at(self, store):
        store.submit(JobRecord.create("text"))
        claimed = store.claim_next("w")
        assert claimed.claimed_at is not None

    def test_claim_priority_order(self, store):
        batch_job = JobRecord.create("batch", workload_type=WorkloadType.BATCH)
        interactive_job = JobRecord.create("interactive", workload_type=WorkloadType.INTERACTIVE)
        store.submit(batch_job)
        store.submit(interactive_job)
        claimed = store.claim_next("w")
        assert claimed.job_id == interactive_job.job_id

    def test_claim_removes_job_from_queue(self, store):
        store.submit(JobRecord.create("text"))
        store.claim_next("w1")
        assert store.claim_next("w2") is None


class TestUpdateStatus:
    def test_update_to_succeeded(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        store.update_status(job.job_id, JobStatus.SUCCEEDED, output_path="/tmp/out.pptx")
        updated = store.get(job.job_id)
        assert updated.status == JobStatus.SUCCEEDED
        assert updated.output_path == "/tmp/out.pptx"
        assert updated.completed_at is not None

    def test_update_to_failed_stores_error(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        store.update_status(
            job.job_id, JobStatus.FAILED,
            error_category="validation",
            error_message="bad input",
        )
        updated = store.get(job.job_id)
        assert updated.error_category == "validation"
        assert updated.error_message == "bad input"

    def test_update_retrying_increments_retry_count(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        store.update_status(job.job_id, JobStatus.RETRYING, retry_count=1)
        assert store.get(job.job_id).retry_count == 1

    def test_update_non_terminal_does_not_set_completed_at(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        store.update_status(job.job_id, JobStatus.RETRYING)
        assert store.get(job.job_id).completed_at is None


class TestCancel:
    def test_cancel_queued_job(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        result = store.cancel(job.job_id)
        assert result == "cancelled"
        assert store.get(job.job_id).status == JobStatus.CANCELLED

    def test_cancel_running_job_returns_cancellation_requested(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        store.claim_next("w")
        result = store.cancel(job.job_id)
        assert result == "cancellation_requested"
        assert store.get(job.job_id).status == JobStatus.CANCELLATION_REQUESTED

    def test_cancel_nonexistent_returns_none(self, store):
        assert store.cancel("nonexistent") is None

    def test_cancel_already_cancelled_returns_none(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        store.cancel(job.job_id)
        assert store.cancel(job.job_id) is None


class TestListStaleRunning:
    def test_stale_running_job_returned(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        store.claim_next("w")
        # Use a negative timeout — any running job claimed before "now" is stale
        stale = store.list_stale_running(timedelta(seconds=-1))
        assert any(j.job_id == job.job_id for j in stale)

    def test_recent_running_job_not_stale(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        store.claim_next("w")
        stale = store.list_stale_running(timedelta(hours=1))
        assert all(j.job_id != job.job_id for j in stale)

    def test_queued_job_not_in_stale_list(self, store):
        job = JobRecord.create("text")
        store.submit(job)
        stale = store.list_stale_running(timedelta(seconds=-1))
        assert all(j.job_id != job.job_id for j in stale)


class TestFromSettings:
    def test_from_settings_uses_job_db_file(self, tmp_path):
        from pptgen.config import RuntimeSettings, override_settings
        settings = RuntimeSettings(job_db_path=str(tmp_path / "custom.db"))
        override_settings(settings)
        try:
            store = SQLiteJobStore.from_settings(settings)
            store.close()
            assert (tmp_path / "custom.db").exists()
        finally:
            override_settings(None)
