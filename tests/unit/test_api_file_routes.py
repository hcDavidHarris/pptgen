"""Tests for GET /v1/files/download endpoint."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from pptgen.api.server import app

client = TestClient(app)

_ALLOWED_BASE = Path(tempfile.gettempdir()) / "pptgen_api"


def _make_temp_pptx(content: bytes = b"FAKE-PPTX") -> Path:
    """Create a real temp file inside the allowed base directory."""
    subdir = _ALLOWED_BASE / "test_file_routes"
    subdir.mkdir(parents=True, exist_ok=True)
    p = subdir / "output.pptx"
    p.write_bytes(content)
    return p


class TestFileDownload:
    def test_serves_file_in_allowed_dir(self):
        p = _make_temp_pptx()
        r = client.get(f"/v1/files/download?path={p}")
        assert r.status_code == 200

    def test_response_has_pptx_content_type(self):
        p = _make_temp_pptx()
        r = client.get(f"/v1/files/download?path={p}")
        assert "presentationml" in r.headers["content-type"]

    def test_response_body_matches_file(self):
        content = b"FAKE-PPTX-CONTENT"
        p = _make_temp_pptx(content)
        r = client.get(f"/v1/files/download?path={p}")
        assert r.content == content

    def test_returns_404_for_missing_file(self):
        missing = _ALLOWED_BASE / "nonexistent" / "output.pptx"
        r = client.get(f"/v1/files/download?path={missing}")
        assert r.status_code == 404

    def test_returns_403_for_path_outside_allowed_dir(self):
        r = client.get("/v1/files/download?path=/etc/passwd")
        assert r.status_code == 403

    def test_returns_403_for_traversal_attempt(self):
        traversal = str(_ALLOWED_BASE / ".." / ".." / "etc" / "passwd")
        r = client.get(f"/v1/files/download?path={traversal}")
        assert r.status_code == 403
