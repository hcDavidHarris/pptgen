"""Tests for run inspection API endpoints."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.artifacts.models import ArtifactRecord, ArtifactType
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.runs.models import RunRecord, RunSource, RunStatus
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


class TestGetRun:
    def test_get_existing_run_200(self, client_with_stores):
        client, run_store, *_ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        resp = client.get(f"/v1/runs/{run.run_id}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == run.run_id

    def test_get_nonexistent_run_404(self, client_with_stores):
        client, *_ = client_with_stores
        assert client.get("/v1/runs/nonexistent").status_code == 404

    def test_get_run_has_status(self, client_with_stores):
        client, run_store, *_ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        data = client.get(f"/v1/runs/{run.run_id}").json()
        assert data["status"] == "running"

    def test_get_run_has_source(self, client_with_stores):
        client, run_store, *_ = client_with_stores
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)
        data = client.get(f"/v1/runs/{run.run_id}").json()
        assert data["source"] == "api_async"

    def test_get_run_has_mode(self, client_with_stores):
        client, run_store, *_ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC, mode="deterministic")
        run_store.create(run)
        data = client.get(f"/v1/runs/{run.run_id}").json()
        assert data["mode"] == "deterministic"

    def test_get_run_has_started_at(self, client_with_stores):
        client, run_store, *_ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        data = client.get(f"/v1/runs/{run.run_id}").json()
        assert data["started_at"] is not None

    def test_get_run_no_store_returns_503(self, tmp_path):
        app.state.run_store = None
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/runs/any")
        assert resp.status_code == 503


class TestListRunArtifacts:
    def test_list_empty_artifacts(self, client_with_stores):
        client, run_store, *_ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        resp = client.get(f"/v1/runs/{run.run_id}/artifacts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_registered_artifacts(self, client_with_stores):
        client, run_store, artifact_store, _ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        art = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path=f"runs/{run.run_id}/output.pptx",
            size_bytes=1024, checksum="sha256:abc",
        )
        artifact_store.register(art)
        resp = client.get(f"/v1/runs/{run.run_id}/artifacts")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_artifacts_for_nonexistent_run_404(self, client_with_stores):
        client, *_ = client_with_stores
        assert client.get("/v1/runs/nonexistent/artifacts").status_code == 404

    def test_artifact_response_has_type(self, client_with_stores):
        client, run_store, artifact_store, _ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        art = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path=f"runs/{run.run_id}/spec.json",
            size_bytes=100, checksum="sha256:x",
        )
        artifact_store.register(art)
        data = client.get(f"/v1/runs/{run.run_id}/artifacts").json()
        assert data[0]["artifact_type"] == "spec"


class TestGetRunManifest:
    def test_get_manifest_404_no_manifest_path(self, client_with_stores):
        client, run_store, *_ = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        resp = client.get(f"/v1/runs/{run.run_id}/manifest")
        assert resp.status_code == 404

    def test_get_manifest_200_with_file(self, client_with_stores):
        client, run_store, artifact_store, artifact_storage = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)

        # Create manifest file in durable store
        run_dir = artifact_storage.ensure_run_dir(run.run_id)
        manifest_file = run_dir / "manifest.json"
        manifest_file.write_text('{"manifest_version": "1.0", "run_id": "' + run.run_id + '"}')
        manifest_rel = artifact_storage.relative_path(run.run_id, "manifest.json")

        run_store.update_status(
            run.run_id, RunStatus.SUCCEEDED, manifest_path=manifest_rel
        )

        resp = client.get(f"/v1/runs/{run.run_id}/manifest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run.run_id
