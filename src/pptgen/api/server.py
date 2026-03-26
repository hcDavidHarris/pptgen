"""pptgen FastAPI application.

Exposes the ``app`` object for use with an ASGI server (e.g. uvicorn)::

    uvicorn pptgen.api.server:app --reload

Or run directly via the CLI::

    python -m pptgen.api.server
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from ..runtime.startup import assert_startup_healthy
from .artifact_routes import router as artifacts_router
from .file_routes import file_router
from .job_routes import router as jobs_router
from .routes import router
from .run_routes import router as runs_router
from .system_routes import router as system_router
from .template_routes import router as template_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup validation and initialize background services."""
    from datetime import timedelta

    from ..jobs.sqlite_store import SQLiteJobStore
    from ..jobs.worker import JobWorker
    from ..runtime.workspace import WorkspaceManager

    from ..artifacts.sqlite_store import SQLiteArtifactStore
    from ..artifacts.storage import ArtifactStorage
    from ..artifacts.promoter import ArtifactPromoter
    from ..runs.sqlite_store import SQLiteRunStore
    from .service import set_artifact_services

    import logging as _logging
    from ..observability.structured_logger import JsonFormatter

    settings = get_settings()

    # Configure root logger level and optional JSON formatting
    log_level = getattr(_logging, settings.log_level.upper(), _logging.INFO)
    root_logger = _logging.getLogger()
    root_logger.setLevel(log_level)
    if settings.log_json_format and not any(
        isinstance(h.formatter, JsonFormatter) for h in root_logger.handlers
    ):
        _handler = _logging.StreamHandler()
        _handler.setFormatter(JsonFormatter())
        root_logger.addHandler(_handler)

    assert_startup_healthy(settings)

    job_store = SQLiteJobStore.from_settings(settings)
    app.state.job_store = job_store

    # Artifact and run stores (Stage 6C)
    run_store = SQLiteRunStore.from_settings(settings)
    artifact_store = SQLiteArtifactStore.from_settings(settings)
    artifact_storage = ArtifactStorage.from_settings(settings)
    promoter = ArtifactPromoter(artifact_storage, artifact_store, run_store)

    app.state.run_store = run_store
    app.state.artifact_store = artifact_store
    app.state.artifact_storage = artifact_storage
    app.state.promoter = promoter

    # Wire promoter into sync path
    set_artifact_services(promoter, run_store)

    # Template registry (Phase 8 Stage 1)
    import logging as _tlog
    from ..templates.store import load_registry as _load_template_registry
    try:
        app.state.template_registry = _load_template_registry()
    except Exception as _exc:
        _tlog.getLogger(__name__).warning("Template registry not loaded: %s", _exc)
        app.state.template_registry = None

    wm = WorkspaceManager.from_settings(settings)
    worker = JobWorker(
        store=job_store,
        workspace_manager=wm,
        poll_interval=settings.worker_poll_interval_seconds,
        stale_timeout=timedelta(minutes=settings.worker_stale_job_timeout_minutes),
        max_retries=settings.max_job_retries,
        run_store=run_store,
        artifact_store=artifact_store,
        promoter=promoter,
    )
    worker.start()
    app.state.job_worker = worker

    yield

    # Shutdown
    worker.stop(timeout=10.0)
    wm.cleanup_older_than(hours=settings.workspace_ttl_hours)

    from ..artifacts.retention import RetentionManager
    retention_mgr = RetentionManager(artifact_store, artifact_storage)
    retention_mgr.run_cleanup(
        longest_hours=settings.artifact_retention_longest_hours,
        medium_hours=settings.artifact_retention_medium_hours,
        shorter_hours=settings.artifact_retention_shorter_hours,
    )

    job_store.close()
    run_store.close()
    artifact_store.close()
    # Reset module-level artifact services
    set_artifact_services(None, None)


app = FastAPI(
    title="pptgen API",
    description=(
        "REST API for the pptgen presentation generation platform.  "
        "Wraps the full generation pipeline — from raw text to .pptx."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS origins are driven by settings; fall back to localhost dev server defaults.
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_settings.api_cors_origins) + ["http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(file_router)
app.include_router(jobs_router)
app.include_router(runs_router)
app.include_router(artifacts_router)
app.include_router(system_router)
app.include_router(template_router)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("pptgen.api.server:app", host="0.0.0.0", port=8000, reload=True)
