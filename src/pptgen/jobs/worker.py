"""Background worker thread for job execution."""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..errors import PptgenError
from ..pipeline.generation_pipeline import generate_presentation
from ..runtime.run_context import RunContext
from ..runtime.workspace import WorkspaceManager
from .models import JobRecord, JobStatus
from .retry import get_backoff_seconds, is_retryable
from .store import AbstractJobStore

logger = logging.getLogger(__name__)

from ..observability import get_logger as _get_structured_logger
_slog = _get_structured_logger(__name__)


class JobWorker:
    """Single daemon thread that claims and executes queued jobs.

    Crash recovery: on startup, any jobs left in 'running' state beyond
    ``stale_timeout`` are reset to 'retrying' (or 'failed' if max retries
    exceeded) before the poll loop begins.
    """

    def __init__(
        self,
        store: AbstractJobStore,
        workspace_manager: WorkspaceManager,
        poll_interval: float = 2.0,
        stale_timeout: timedelta = timedelta(minutes=15),
        max_retries: int = 3,
        run_store=None,
        artifact_store=None,
        promoter=None,
    ) -> None:
        self._store = store
        self._wm = workspace_manager
        self._poll_interval = poll_interval
        self._stale_timeout = stale_timeout
        self._max_retries = max_retries
        self._worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._run_store = run_store
        self._artifact_store = artifact_store
        self._promoter = promoter

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background worker thread."""
        self._thread = threading.Thread(
            target=self._loop,
            name="pptgen-job-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("JobWorker started: %s", self._worker_id)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the worker to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("JobWorker stopped: %s", self._worker_id)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        self._recover_stale_jobs()
        while not self._stop_event.is_set():
            job = self._store.claim_next(self._worker_id)
            if job is None:
                self._stop_event.wait(timeout=self._poll_interval)
                continue
            self._execute(job)

    def _recover_stale_jobs(self) -> None:
        """Reset stale running jobs left from a previous crash."""
        stale = self._store.list_stale_running(self._stale_timeout)
        for job in stale:
            logger.warning(
                "Recovering stale job %s (retry_count=%d)", job.job_id, job.retry_count
            )
            if job.retry_count < job.max_retries:
                self._store.update_status(
                    job.job_id,
                    JobStatus.RETRYING,
                    retry_count=job.retry_count + 1,
                )
            else:
                self._store.update_status(
                    job.job_id,
                    JobStatus.FAILED,
                    error_category="system",
                    error_message="Job stale after worker restart; max retries exceeded.",
                )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute(self, job: JobRecord) -> None:
        logger.info("Executing job %s (retry=%d)", job.job_id, job.retry_count)
        run = None
        ws = None
        ctx = None
        try:
            ws = self._wm.create(job.run_id)
            ctx = RunContext(
                run_id=job.run_id,
                request_id=job.request_id,
                mode=job.mode,
                template_id=job.template_id,
            )

            # Create run record if promoter is wired in
            if self._run_store is not None:
                from ..runs.models import RunRecord, RunSource
                run = RunRecord.create(
                    source=RunSource.API_ASYNC,
                    run_id=job.run_id,
                    job_id=job.job_id,
                    request_id=job.request_id,
                    mode=job.mode,
                    template_id=job.template_id,
                    input_text=job.input_text,
                    action_type=job.action_type,
                    source_run_id=job.source_run_id,
                )
                self._run_store.create(run)
                _slog.job_claimed(job.job_id, run_id=job.run_id, worker_id=self._worker_id)

            generate_presentation(
                job.input_text,
                output_path=ws.output_path,
                template_id=job.template_id,
                mode=job.mode,
                run_context=ctx,
            )

            if self._promoter is not None and run is not None:
                self._promoter.promote(
                    run=run,
                    workspace_root=ws.root,
                    artifacts_subdir=ws.root / "artifacts",
                    run_context_dict=ctx.as_dict(),
                    total_ms=ctx.total_ms(),
                )

            # Check if cancellation was requested while we were executing
            refreshed = self._store.get(job.job_id)
            if refreshed is not None and refreshed.status == JobStatus.CANCELLATION_REQUESTED:
                self._store.update_status(job.job_id, JobStatus.CANCELLED)
                logger.info("Job %s cancelled post-execution", job.job_id)
                return

            self._store.update_status(
                job.job_id,
                JobStatus.SUCCEEDED,
                output_path=str(ws.output_path),
                playbook_id=ctx.playbook_id,
            )
            logger.info("Job %s succeeded", job.job_id)
            _slog.job_completed(job.job_id, run_id=job.run_id)
        except PptgenError as exc:
            self._handle_failure(job, exc, run=run, ws=ws, ctx=ctx)
        except Exception as exc:
            self._handle_failure(job, exc, category="system", run=run, ws=ws, ctx=ctx)

    def _handle_failure(
        self,
        job: JobRecord,
        exc: Exception,
        category: Optional[str] = None,
        run=None,
        ws=None,
        ctx=None,
    ) -> None:
        cat = category
        if cat is None and isinstance(exc, PptgenError):
            cat = exc.category.value if hasattr(exc, "category") else "system"
        cat = cat or "system"
        message = str(exc)

        logger.warning("Job %s failed (category=%s): %s", job.job_id, cat, message)
        _slog.job_failed(job.job_id, run_id=job.run_id, error=message)

        # Record failure in run registry if promoter is wired in
        if self._promoter is not None and run is not None and ws is not None:
            try:
                self._promoter.promote(
                    run=run,
                    workspace_root=ws.root,
                    artifacts_subdir=ws.root / "artifacts",
                    run_context_dict=ctx.as_dict() if ctx else None,
                    error_category=cat,
                    error_message=message,
                    total_ms=ctx.total_ms() if ctx else None,
                )
            except Exception as promote_exc:
                logger.warning(
                    "Promoter failed for job %s: %s", job.job_id, promote_exc
                )

        new_retry_count = job.retry_count + 1
        can_retry = is_retryable(cat) and new_retry_count <= job.max_retries

        if can_retry:
            backoff = get_backoff_seconds(new_retry_count)
            self._store.update_status(
                job.job_id,
                JobStatus.RETRYING,
                error_category=cat,
                error_message=message,
                retry_count=new_retry_count,
            )
            logger.info("Job %s scheduled for retry in %.0fs", job.job_id, backoff)
            self._stop_event.wait(timeout=backoff)
        else:
            self._store.update_status(
                job.job_id,
                JobStatus.FAILED,
                error_category=cat,
                error_message=message,
                retry_count=new_retry_count,
            )
