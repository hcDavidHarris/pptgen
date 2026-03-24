"""Tests for JobWorker — uses SQLiteJobStore with tmp_path."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from pptgen.jobs.models import JobRecord, JobStatus
from pptgen.jobs.sqlite_store import SQLiteJobStore
from pptgen.jobs.worker import JobWorker
from pptgen.runtime.workspace import WorkspaceManager


@pytest.fixture
def store(tmp_path: Path):
    s = SQLiteJobStore(db_path=tmp_path / "jobs.db")
    yield s
    s.close()


@pytest.fixture
def wm(tmp_path: Path):
    return WorkspaceManager(base=tmp_path / "ws")


class TestWorkerLifecycle:
    def test_start_stop(self, store, wm):
        worker = JobWorker(store=store, workspace_manager=wm, poll_interval=0.05)
        worker.start()
        assert worker.is_running is True
        worker.stop(timeout=1.0)
        assert worker.is_running is False

    def test_not_running_before_start(self, store, wm):
        worker = JobWorker(store=store, workspace_manager=wm)
        assert worker.is_running is False


class TestWorkerProcessesJobs:
    def test_worker_processes_queued_job(self, store, wm):
        worker = JobWorker(store=store, workspace_manager=wm, poll_interval=0.05)
        job = JobRecord.create(
            "Meeting notes. Attendees: Alice. Action items and follow-up."
        )
        store.submit(job)
        worker.start()
        deadline = time.time() + 5.0
        while time.time() < deadline:
            fetched = store.get(job.job_id)
            if fetched and fetched.is_terminal():
                break
            time.sleep(0.1)
        worker.stop(timeout=2.0)
        final = store.get(job.job_id)
        assert final is not None
        assert final.status == JobStatus.SUCCEEDED

    def test_succeeded_job_has_output_path(self, store, wm):
        worker = JobWorker(store=store, workspace_manager=wm, poll_interval=0.05)
        job = JobRecord.create(
            "Meeting notes. Attendees: Alice. Action items and follow-up."
        )
        store.submit(job)
        worker.start()
        deadline = time.time() + 5.0
        while time.time() < deadline:
            fetched = store.get(job.job_id)
            if fetched and fetched.is_terminal():
                break
            time.sleep(0.1)
        worker.stop(timeout=2.0)
        final = store.get(job.job_id)
        assert final.output_path is not None
        assert final.output_path.endswith("output.pptx")


class TestWorkerCrashRecovery:
    def test_worker_recovers_stale_job_on_startup(self, store, wm):
        """Stale running job should be reset to retrying on worker start."""
        job = JobRecord.create("input text")
        store.submit(job)
        # Manually set to running with ancient claimed_at (simulates crash)
        store._conn.execute(
            "UPDATE jobs SET status='running', claimed_at='2000-01-01T00:00:00+00:00' WHERE job_id=?",
            (job.job_id,),
        )
        store._conn.commit()

        worker = JobWorker(store=store, workspace_manager=wm, poll_interval=0.05)
        worker._recover_stale_jobs()

        recovered = store.get(job.job_id)
        assert recovered.status in (JobStatus.RETRYING, JobStatus.FAILED)

    def test_stale_job_exceeding_max_retries_is_failed(self, store, wm):
        job = JobRecord.create("text", max_retries=0)
        store.submit(job)
        store._conn.execute(
            "UPDATE jobs SET status='running', claimed_at='2000-01-01T00:00:00+00:00',"
            " retry_count=0, max_retries=0 WHERE job_id=?",
            (job.job_id,),
        )
        store._conn.commit()

        worker = JobWorker(store=store, workspace_manager=wm)
        worker._recover_stale_jobs()

        assert store.get(job.job_id).status == JobStatus.FAILED
