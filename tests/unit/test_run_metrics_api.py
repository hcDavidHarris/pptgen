"""Tests for GET /v1/runs/{run_id}/metrics endpoint."""
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


class TestRunMetrics:
    def test_metrics_nonexistent_run_404(self, client_with_stores):
        client, _ = client_with_stores
        resp = client.get("/v1/runs/nonexistent/metrics")
        assert resp.status_code == 404

    def test_metrics_empty_stage_timings(self, client_with_stores):
        client, run_store = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        run_store.update_status(run.run_id, RunStatus.SUCCEEDED)
        resp = client.get(f"/v1/runs/{run.run_id}/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stage_timings"] == []
        assert data["slowest_stage"] is None
        assert data["fastest_stage"] is None

    def test_metrics_with_stage_timings(self, client_with_stores):
        client, run_store = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        timings = [
            {"stage": "planning", "duration_ms": 100.0},
            {"stage": "rendering", "duration_ms": 500.0},
            {"stage": "spec", "duration_ms": 50.0},
        ]
        run_store.update_status(run.run_id, RunStatus.SUCCEEDED,
                                 stage_timings=timings, total_ms=650.0, artifact_count=3)
        resp = client.get(f"/v1/runs/{run.run_id}/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slowest_stage"] == "rendering"
        assert data["fastest_stage"] == "spec"
        assert data["total_ms"] == 650.0
        assert data["artifact_count"] == 3

    def test_metrics_stage_timings_with_none_duration(self, client_with_stores):
        client, run_store = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        timings = [
            {"stage": "planning", "duration_ms": None},
            {"stage": "rendering", "duration_ms": 200.0},
        ]
        run_store.update_status(run.run_id, RunStatus.SUCCEEDED, stage_timings=timings)
        resp = client.get(f"/v1/runs/{run.run_id}/metrics")
        assert resp.status_code == 200
        data = resp.json()
        # Only the non-None entry should be considered for slowest/fastest
        assert data["slowest_stage"] == "rendering"
        assert data["fastest_stage"] == "rendering"

    def test_metrics_run_id_in_response(self, client_with_stores):
        client, run_store = client_with_stores
        run = RunRecord.create(source=RunSource.API_SYNC)
        run_store.create(run)
        resp = client.get(f"/v1/runs/{run.run_id}/metrics")
        assert resp.json()["run_id"] == run.run_id
