"""Tests for GET /v1/runs (list) endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
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
    yield client, run_store
    run_store.close()
    artifact_store.close()
    app.state.run_store = None
    app.state.artifact_store = None
    app.state.artifact_storage = None


class TestListRuns:
    def test_list_runs_empty(self, client_with_stores):
        client, _ = client_with_stores
        resp = client.get("/v1/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["runs"] == []
        assert data["total"] == 0

    def test_list_runs_returns_runs(self, client_with_stores):
        client, run_store = client_with_stores
        r1 = RunRecord.create(source=RunSource.API_SYNC)
        r2 = RunRecord.create(source=RunSource.CLI)
        run_store.create(r1)
        run_store.create(r2)
        resp = client.get("/v1/runs")
        assert resp.status_code == 200
        assert len(resp.json()["runs"]) == 2

    def test_list_runs_filter_by_status(self, client_with_stores):
        client, run_store = client_with_stores
        r1 = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(r1)
        run_store.update_status(r1.run_id, RunStatus.SUCCEEDED)
        r2 = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(r2)
        run_store.update_status(r2.run_id, RunStatus.FAILED)

        resp = client.get("/v1/runs?status=succeeded")
        assert resp.status_code == 200
        items = resp.json()["runs"]
        assert len(items) == 1
        assert items[0]["status"] == "succeeded"

    def test_list_runs_filter_by_source(self, client_with_stores):
        client, run_store = client_with_stores
        r1 = RunRecord.create(source=RunSource.CLI)
        run_store.create(r1)
        r2 = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(r2)

        resp = client.get("/v1/runs?source=cli")
        assert resp.status_code == 200
        items = resp.json()["runs"]
        assert len(items) == 1
        assert items[0]["source"] == "cli"

    def test_list_runs_limit_and_offset(self, client_with_stores):
        client, run_store = client_with_stores
        for _ in range(5):
            r = RunRecord.create(source=RunSource.API_SYNC)
            run_store.create(r)

        resp = client.get("/v1/runs?limit=2&offset=0")
        assert len(resp.json()["runs"]) == 2

        resp2 = client.get("/v1/runs?limit=2&offset=2")
        assert len(resp2.json()["runs"]) == 2

    def test_list_runs_response_has_run_id(self, client_with_stores):
        client, run_store = client_with_stores
        r = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(r)
        items = client.get("/v1/runs").json()["runs"]
        assert items[0]["run_id"] == r.run_id

    def test_list_runs_does_not_shadow_run_id_route(self, client_with_stores):
        client, run_store = client_with_stores
        r = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(r)
        # GET /v1/runs/{run_id} should still work after adding GET /v1/runs
        resp = client.get(f"/v1/runs/{r.run_id}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == r.run_id
