"""Minimal file-serving route for generated PPTX downloads.

Only files inside the pptgen_api temp subtree may be served — all other
paths are rejected with 403.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import get_settings

file_router = APIRouter(prefix="/v1", tags=["files"])


@file_router.get("/files/download")
def download_file(path: str) -> FileResponse:
    """Serve a generated file by absolute path.

    The *path* must reside inside ``$TMPDIR/pptgen_api/`` to prevent
    directory traversal.  Returns the file as an attachment.

    Args:
        path: Absolute filesystem path to the generated ``.pptx`` file.

    Raises:
        HTTPException 403: Path is outside the allowed subtree.
        HTTPException 404: File does not exist.
    """
    resolved = Path(path).resolve()
    allowed = get_settings().workspace_base_path.resolve()

    if not str(resolved).startswith(str(allowed)):
        raise HTTPException(status_code=403, detail="Access denied.")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(
        path=resolved,
        filename=resolved.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
