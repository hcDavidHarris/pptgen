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
from .file_routes import file_router
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup validation before the server begins accepting requests."""
    settings = get_settings()
    assert_startup_healthy(settings)
    yield
    # Shutdown: no-op in Stage 6A. TTL workspace cleanup scheduled in Stage 6B.


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


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("pptgen.api.server:app", host="0.0.0.0", port=8000, reload=True)
