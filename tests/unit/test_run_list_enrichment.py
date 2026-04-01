"""Tests for RunListItemResponse enrichment and ?mode= filter (Phase 7 PR 1)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pptgen.api.schemas import RunListItemResponse
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore


# ---------------------------------------------------------------------------
# Schema tests — new fields present and defaulted correctly
# ---------------------------------------------------------------------------

class TestRunListItemResponseSchema:
    def test_mode_field_present_with_default(self):
        item = RunListItemResponse(
            run_id="r1",
            status="succeeded",
            source="api_sync",
            started_at="2026-03-24T10:00:00",
        )
        assert item.mode == "deterministic"

    def test_template_id_field_present_nullable(self):
        item = RunListItemResponse(
            run_id="r1",
            status="succeeded",
            source="api_sync",
            started_at="2026-03-24T10:00:00",
        )
        assert item.template_id is None

    def test_playbook_id_field_present_nullable(self):
        item = RunListItemResponse(
            run_id="r1",
            status="succeeded",
            source="api_sync",
            started_at="2026-03-24T10:00:00",
        )
        assert item.playbook_id is None

    def test_fields_populated_when_provided(self):
        item = RunListItemResponse(
            run_id="r1",
            status="succeeded",
            source="api_sync",
            started_at="2026-03-24T10:00:00",
            mode="ai",
            template_id="hc-default",
            playbook_id="meeting-notes-to-eos-rocks",
        )
        assert item.mode == "ai"
        assert item.template_id == "hc-default"
        assert item.playbook_id == "meeting-notes-to-eos-rocks"


# ---------------------------------------------------------------------------
# SQLiteRunStore list_runs — mode filter
# ---------------------------------------------------------------------------

def _make_run(run_id: str, mode: str = "deterministic") -> RunRecord:
    return RunRecord(
        run_id=run_id,
        status=RunStatus.SUCCEEDED,
        source=RunSource.API_SYNC,
        mode=mode,
        profile="dev",
        started_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture()
def store(tmp_path: Path) -> SQLiteRunStore:
    s = SQLiteRunStore(tmp_path / "runs.db")
    yield s
    s.close()


class TestSQLiteRunStoreListRunsModeFilter:
    def test_no_mode_filter_returns_all(self, store: SQLiteRunStore):
        store.create(_make_run("r1", "deterministic"))
        store.create(_make_run("r2", "ai"))
        runs = store.list_runs()
        assert len(runs) == 2

    def test_mode_filter_deterministic(self, store: SQLiteRunStore):
        store.create(_make_run("r1", "deterministic"))
        store.create(_make_run("r2", "ai"))
        runs = store.list_runs(mode="deterministic")
        assert len(runs) == 1
        assert runs[0].run_id == "r1"

    def test_mode_filter_ai(self, store: SQLiteRunStore):
        store.create(_make_run("r1", "deterministic"))
        store.create(_make_run("r2", "ai"))
        runs = store.list_runs(mode="ai")
        assert len(runs) == 1
        assert runs[0].run_id == "r2"

    def test_mode_filter_nonexistent_returns_empty(self, store: SQLiteRunStore):
        store.create(_make_run("r1", "deterministic"))
        runs = store.list_runs(mode="unknown-mode")
        assert runs == []

    def test_mode_filter_combined_with_status(self, store: SQLiteRunStore):
        store.create(_make_run("r1", "deterministic"))
        store.create(_make_run("r2", "ai"))
        store.update_status("r2", RunStatus.FAILED)
        runs = store.list_runs(status="failed", mode="ai")
        assert len(runs) == 1
        assert runs[0].run_id == "r2"


# ---------------------------------------------------------------------------
# API endpoint — mode, template_id, playbook_id appear in response body
# ---------------------------------------------------------------------------

def _make_app_with_runs(runs: list[RunRecord]):
    """Build a minimal FastAPI app with a pre-populated in-memory run store."""
    from unittest.mock import MagicMock
    from fastapi import FastAPI
    from pptgen.api.run_routes import router

    app = FastAPI()
    app.include_router(router)

    mock_store = MagicMock()
    mock_store.list_runs.return_value = runs

    @app.on_event("startup")
    def _setup():
        app.state.run_store = mock_store

    return app, mock_store


class TestListRunsApiEnrichment:
    def test_response_includes_mode_field(self):
        run = _make_run("r1", "deterministic")
        run.template_id = "hc-default"
        run.playbook_id = "meeting-notes-to-eos-rocks"

        from unittest.mock import MagicMock
        from fastapi import FastAPI
        from pptgen.api.run_routes import router

        app = FastAPI()
        app.include_router(router)
        mock_store = MagicMock()
        mock_store.list_runs.return_value = [run]
        app.state.run_store = mock_store

        client = TestClient(app)
        resp = client.get("/v1/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) == 1
        item = data["runs"][0]
        assert item["mode"] == "deterministic"
        assert item["template_id"] == "hc-default"
        assert item["playbook_id"] == "meeting-notes-to-eos-rocks"

    def test_mode_query_param_forwarded_to_store(self):
        from unittest.mock import MagicMock, call
        from fastapi import FastAPI
        from pptgen.api.run_routes import router

        app = FastAPI()
        app.include_router(router)
        mock_store = MagicMock()
        mock_store.list_runs.return_value = []
        app.state.run_store = mock_store

        client = TestClient(app)
        client.get("/v1/runs?mode=ai")

        mock_store.list_runs.assert_called_once_with(
            limit=50, offset=0, status=None, source=None, mode="ai"
        )

    def test_null_mode_not_forwarded_to_store(self):
        from unittest.mock import MagicMock
        from fastapi import FastAPI
        from pptgen.api.run_routes import router

        app = FastAPI()
        app.include_router(router)
        mock_store = MagicMock()
        mock_store.list_runs.return_value = []
        app.state.run_store = mock_store

        client = TestClient(app)
        client.get("/v1/runs")

        mock_store.list_runs.assert_called_once_with(
            limit=50, offset=0, status=None, source=None, mode=None
        )
