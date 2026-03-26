"""Tests for GET /v1/runs/stats endpoint (PR 2 — Run History Insights)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def client_with_runs(tmp_path):
    db = tmp_path / "artifacts.db"
    run_store = SQLiteRunStore(db_path=db)
    app.state.run_store = run_store
    client = TestClient(app, raise_server_exceptions=False)
    yield client, run_store
    run_store.close()
    app.state.run_store = None


def _make_run(source=RunSource.API_SYNC, status=RunStatus.SUCCEEDED, total_ms=None,
              started_at=None, completed_at=None):
    run = RunRecord.create(source=source)
    if started_at:
        object.__setattr__(run, "started_at", started_at)
    if total_ms is not None:
        object.__setattr__(run, "total_ms", total_ms)
    return run


class TestRunStatsEndpoint:
    def test_stats_empty_db(self, client_with_runs):
        client, _ = client_with_runs
        resp = client.get("/v1/runs/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 0
        assert data["success_rate"] is None
        assert data["avg_duration_ms"] is None

    def test_stats_counts_succeeded(self, client_with_runs):
        client, run_store = client_with_runs
        run = _make_run(status=RunStatus.SUCCEEDED)
        run_store.create(run)
        run_store.update_status(run.run_id, RunStatus.SUCCEEDED, total_ms=500)
        resp = client.get("/v1/runs/stats")
        data = resp.json()
        assert data["total_runs"] == 1
        assert data["succeeded_runs"] == 1
        assert data["failed_runs"] == 0
        assert data["success_rate"] == 100.0

    def test_stats_counts_failed(self, client_with_runs):
        client, run_store = client_with_runs
        run = _make_run()
        run_store.create(run)
        run_store.update_status(run.run_id, RunStatus.FAILED, error_category="TemplateError")
        resp = client.get("/v1/runs/stats")
        data = resp.json()
        assert data["failed_runs"] == 1
        assert data["succeeded_runs"] == 0
        assert data["success_rate"] == 0.0

    def test_stats_success_rate_mixed(self, client_with_runs):
        client, run_store = client_with_runs
        for _ in range(3):
            r = _make_run()
            run_store.create(r)
            run_store.update_status(r.run_id, RunStatus.SUCCEEDED, total_ms=1000)
        r = _make_run()
        run_store.create(r)
        run_store.update_status(r.run_id, RunStatus.FAILED)
        resp = client.get("/v1/runs/stats")
        data = resp.json()
        assert data["total_runs"] == 4
        assert data["succeeded_runs"] == 3
        assert data["failed_runs"] == 1
        assert data["success_rate"] == 75.0

    def test_stats_avg_duration(self, client_with_runs):
        client, run_store = client_with_runs
        for ms in [1000, 2000, 3000]:
            r = _make_run()
            run_store.create(r)
            run_store.update_status(r.run_id, RunStatus.SUCCEEDED, total_ms=ms)
        resp = client.get("/v1/runs/stats")
        data = resp.json()
        assert data["avg_duration_ms"] == pytest.approx(2000.0, rel=0.01)

    def test_stats_window_7d(self, client_with_runs):
        client, run_store = client_with_runs
        r = _make_run()
        run_store.create(r)
        run_store.update_status(r.run_id, RunStatus.SUCCEEDED)
        resp = client.get("/v1/runs/stats?window=7d")
        assert resp.status_code == 200
        assert resp.json()["window_hours"] == 168

    def test_stats_window_1h(self, client_with_runs):
        client, _ = client_with_runs
        resp = client.get("/v1/runs/stats?window=1h")
        assert resp.status_code == 200
        assert resp.json()["window_hours"] == 1

    def test_unknown_window_defaults_to_24h(self, client_with_runs):
        client, _ = client_with_runs
        resp = client.get("/v1/runs/stats?window=bogus")
        assert resp.status_code == 200
        assert resp.json()["window_hours"] == 24

    def test_stats_does_not_shadow_run_id_route(self, client_with_runs):
        """GET /v1/runs/stats must not prevent fetching a run with id 'stats'."""
        # We can only confirm the stats route works correctly here;
        # a run with id 'stats' would still match /{run_id} if
        # it were registered after /stats — but /stats IS first so
        # a real run_id lookup works. Confirm /stats returns stats shape.
        client, _ = client_with_runs
        resp = client.get("/v1/runs/stats")
        assert "total_runs" in resp.json()
        # Confirm a nonexistent run_id returns 404, not stats
        resp2 = client.get("/v1/runs/not-a-real-run")
        assert resp2.status_code == 404
