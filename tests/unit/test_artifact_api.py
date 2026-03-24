"""Tests for artifact metadata and download API endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.artifacts.models import ArtifactRecord, ArtifactType
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.runs.models import RunRecord, RunSource
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def client_with_stores(tmp_path):
    db = tmp_path / "artifacts.db"
    run_store = SQLiteRunStore(db_path=db)
    artifact_store = SQLiteArtifactStore(db_path=db)
    artifact_storage = ArtifactStorage(base=tmp_path / "store")

    app.state.run_store = run_store
    app.state.artifact_store = artifact_store
    app.state.artifact_storage = artifact_storage

    client = TestClient(app, raise_server_exceptions=False)
    yield client, run_store, artifact_store, artifact_storage

    run_store.close()
    artifact_store.close()
    app.state.run_store = None
    app.state.artifact_store = None
    app.state.artifact_storage = None


class TestGetArtifactMetadata:
    def test_get_metadata_200(self, client_with_stores):
        client, run_store, artifact_store, _ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        art = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path=f"runs/{run.run_id}/output.pptx",
            size_bytes=100, checksum="sha256:x",
        )
        artifact_store.register(art)
        resp = client.get(f"/v1/artifacts/{art.artifact_id}/metadata")
        assert resp.status_code == 200
        assert resp.json()["artifact_id"] == art.artifact_id

    def test_get_metadata_nonexistent_404(self, client_with_stores):
        client, *_ = client_with_stores
        assert client.get("/v1/artifacts/nonexistent/metadata").status_code == 404

    def test_metadata_has_artifact_type(self, client_with_stores):
        client, run_store, artifact_store, _ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        art = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path=f"runs/{run.run_id}/spec.json",
            size_bytes=50, checksum="sha256:y",
        )
        artifact_store.register(art)
        data = client.get(f"/v1/artifacts/{art.artifact_id}/metadata").json()
        assert data["artifact_type"] == "spec"

    def test_metadata_has_visibility(self, client_with_stores):
        client, run_store, artifact_store, _ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        art = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path=f"runs/{run.run_id}/output.pptx",
            size_bytes=100, checksum="sha256:z",
        )
        artifact_store.register(art)
        data = client.get(f"/v1/artifacts/{art.artifact_id}/metadata").json()
        assert data["visibility"] == "downloadable"


class TestDownloadArtifact:
    def test_download_internal_artifact_403(self, client_with_stores):
        client, run_store, artifact_store, _ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        art = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path=f"runs/{run.run_id}/spec.json",
            size_bytes=100, checksum="sha256:y",
        )
        artifact_store.register(art)
        resp = client.get(f"/v1/artifacts/{art.artifact_id}/download")
        assert resp.status_code == 403

    def test_download_nonexistent_404(self, client_with_stores):
        client, *_ = client_with_stores
        assert client.get("/v1/artifacts/nonexistent/download").status_code == 404

    def test_download_pptx_200(self, client_with_stores):
        client, run_store, artifact_store, artifact_storage = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)

        # Write the actual file to durable store
        run_dir = artifact_storage.ensure_run_dir(run.run_id)
        pptx_file = run_dir / "output.pptx"
        pptx_file.write_bytes(b"fake pptx data")

        art = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.PPTX,
            filename="output.pptx",
            relative_path=artifact_storage.relative_path(run.run_id, "output.pptx"),
            size_bytes=14, checksum="sha256:abc",
        )
        artifact_store.register(art)
        resp = client.get(f"/v1/artifacts/{art.artifact_id}/download")
        assert resp.status_code == 200

    def test_download_missing_file_404(self, client_with_stores):
        client, run_store, artifact_store, artifact_storage = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)

        # Register artifact but don't write file
        art = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.PPTX,
            filename="output.pptx",
            relative_path=artifact_storage.relative_path(run.run_id, "output.pptx"),
            size_bytes=14, checksum="sha256:abc",
        )
        artifact_store.register(art)
        resp = client.get(f"/v1/artifacts/{art.artifact_id}/download")
        assert resp.status_code == 404
