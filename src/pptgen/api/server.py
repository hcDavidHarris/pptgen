"""pptgen FastAPI application.

Exposes the ``app`` object for use with an ASGI server (e.g. uvicorn)::

    uvicorn pptgen.api.server:app --reload

Or run directly via the CLI::

    python -m pptgen.api.server
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .file_routes import file_router
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

# Allow the Vite dev server (and any localhost origin) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(file_router)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("pptgen.api.server:app", host="0.0.0.0", port=8000, reload=True)
