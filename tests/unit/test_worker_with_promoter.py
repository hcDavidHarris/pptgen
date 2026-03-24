"""Integration tests for JobWorker with ArtifactPromoter wired in."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from pptgen.artifacts.models import ArtifactType
from pptgen.artifacts.promoter import ArtifactPromoter
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.jobs.models import JobRecord
from pptgen.jobs.sqlite_store import SQLiteJobStore
from pptgen.jobs.worker import JobWorker
from pptgen.runs.models import RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore
from pptgen.runtime.workspace import WorkspaceManager


_MEETING_TEXT = "Meeting notes. Attendees: Alice. Action items and follow-up decisions."
_WORKER_TIMEOUT = 15.0


def _wait_for_terminal(job_store: SQLiteJobStore, job_id: str, timeout: float = _WORKER_TIMEOUT) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = job_store.get(job_id)
        if job and job.is_terminal():
            return True
        time.sleep(0.1)
    return False


@pytest.fixture
def stores(tmp_path):
    db_path = tmp_path / "artifacts.db"
    run_store = SQLiteRunStore(db_path=db_path)
    artifact_store = SQLiteArtifactStore(db_path=db_path)
    storage = ArtifactStorage(base=tmp_path / "store")
    promoter = ArtifactPromoter(storage, artifact_store, run_store)
    job_store = SQLiteJobStore(db_path=tmp_path / "jobs.db")
    wm = WorkspaceManager(base=tmp_path / "ws")
    yield run_store, artifact_store, storage, promoter, job_store, wm
    run_store.close()
    artifact_store.close()
    job_store.close()


class TestWorkerPromoterIntegration:
    def test_worker_promotes_on_success(self, stores):
        run_store, artifact_store, storage, promoter, job_store, wm = stores

        worker = JobWorker(
            store=job_store,
            workspace_manager=wm,
            poll_interval=0.05,
            run_store=run_store,
            artifact_store=artifact_store,
            promoter=promoter,
        )

        job = JobRecord.create(_MEETING_TEXT)
        job_store.submit(job)
        worker.start()
        try:
            assert _wait_for_terminal(job_store, job.job_id), "Job did not complete in time"
        finally:
            worker.stop(timeout=3.0)

        # Job succeeded
        final_job = job_store.get(job.job_id)
        assert final_job.is_terminal()

        # Run record created and succeeded
        run = run_store.get(job.run_id)
        assert run is not None
        assert run.status == RunStatus.SUCCEEDED

    def test_worker_registers_pptx_artifact(self, stores):
        run_store, artifact_store, storage, promoter, job_store, wm = stores

        worker = JobWorker(
            store=job_store,
            workspace_manager=wm,
            poll_interval=0.05,
            run_store=run_store,
            artifact_store=artifact_store,
            promoter=promoter,
        )

        job = JobRecord.create(_MEETING_TEXT)
        job_store.submit(job)
        worker.start()
        try:
            assert _wait_for_terminal(job_store, job.job_id)
        finally:
            worker.stop(timeout=3.0)

        artifacts = artifact_store.list_for_run(job.run_id)
        pptx = [a for a in artifacts if a.artifact_type == ArtifactType.PPTX]
        assert len(pptx) == 1

    def test_worker_pptx_exists_in_durable_store(self, stores):
        run_store, artifact_store, storage, promoter, job_store, wm = stores

        worker = JobWorker(
            store=job_store,
            workspace_manager=wm,
            poll_interval=0.05,
            run_store=run_store,
            artifact_store=artifact_store,
            promoter=promoter,
        )

        job = JobRecord.create(_MEETING_TEXT)
        job_store.submit(job)
        worker.start()
        try:
            assert _wait_for_terminal(job_store, job.job_id)
        finally:
            worker.stop(timeout=3.0)

        artifacts = artifact_store.list_for_run(job.run_id)
        pptx = [a for a in artifacts if a.artifact_type == ArtifactType.PPTX]
        assert len(pptx) == 1
        durable_path = storage.resolve(pptx[0].relative_path)
        assert durable_path.exists()

    def test_worker_without_promoter_still_works(self, stores):
        """Verify backward compatibility: worker works fine without promoter."""
        _, _, _, _, job_store, wm = stores

        worker = JobWorker(
            store=job_store,
            workspace_manager=wm,
            poll_interval=0.05,
        )

        job = JobRecord.create(_MEETING_TEXT)
        job_store.submit(job)
        worker.start()
        try:
            assert _wait_for_terminal(job_store, job.job_id)
        finally:
            worker.stop(timeout=3.0)

        final_job = job_store.get(job.job_id)
        assert final_job.is_terminal()
