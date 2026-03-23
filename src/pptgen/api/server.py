"""pptgen FastAPI application.

Exposes the ``app`` object for use with an ASGI server (e.g. uvicorn)::

    uvicorn pptgen.api.server:app --reload

Or run directly via the CLI::

    python -m pptgen.api.server
"""

from __future__ import annotations

from fastapi import FastAPI

from .routes import router

app = FastAPI(
    title="pptgen API",
    description=(
        "REST API for the pptgen presentation generation platform.  "
        "Wraps the full generation pipeline — from raw text to .pptx."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("pptgen.api.server:app", host="0.0.0.0", port=8000, reload=True)
