"""Tests for template metadata exposure in run API responses — Phase 8 Stage 2."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def client_with_run_store(tmp_path):
    db = tmp_path / "artifacts.db"
    run_store = SQLiteRunStore(db_path=db)
    artifact_store = SQLiteArtifactStore(db_path=db)
    artifact_storage = ArtifactStorage(base=tmp_path / "store")

    app.state.run_store = run_store
    app.state.artifact_store = artifact_store
    app.state.artifact_storage = artifact_storage
    app.state.job_store = None

    client = TestClient(app, raise_server_exceptions=False)
    yield client, run_store
    run_store.close()
    artifact_store.close()
    app.state.run_store = None
    app.state.artifact_store = None


def _create_run_with_template(
    store: SQLiteRunStore,
    run_id: str = "run-tmpl-001",
    template_id: str = "exec_brief",
    template_version: str = "1.0.0",
    template_revision_hash: str = "ab12cd34ef56ab12",
) -> RunRecord:
    run = RunRecord.create(
        source=RunSource.API_SYNC,
        run_id=run_id,
        template_id=template_id,
        template_version=template_version,
        template_revision_hash=template_revision_hash,
    )
    store.create(run)
    return run


# ---------------------------------------------------------------------------
# GET /v1/runs/{run_id} — template fields present
# ---------------------------------------------------------------------------

def test_run_detail_includes_template_id(client_with_run_store):
    client, store = client_with_run_store
    _create_run_with_template(store, template_id="exec_brief")
    resp = client.get("/v1/runs/run-tmpl-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == "exec_brief"


def test_run_detail_includes_template_version(client_with_run_store):
    client, store = client_with_run_store
    _create_run_with_template(store, template_version="2.3.1")
    resp = client.get("/v1/runs/run-tmpl-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_version"] == "2.3.1"


def test_run_detail_includes_template_revision_hash(client_with_run_store):
    client, store = client_with_run_store
    _create_run_with_template(store, template_revision_hash="deadbeef01234567")
    resp = client.get("/v1/runs/run-tmpl-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_revision_hash"] == "deadbeef01234567"


def test_run_detail_template_fields_null_when_absent(client_with_run_store):
    client, store = client_with_run_store
    run = RunRecord.create(source=RunSource.API_SYNC, run_id="run-no-tmpl")
    store.create(run)
    resp = client.get("/v1/runs/run-no-tmpl")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] is None
    assert data["template_version"] is None
    assert data["template_revision_hash"] is None


# ---------------------------------------------------------------------------
# GET /v1/runs — list item includes template_id
# ---------------------------------------------------------------------------

def test_run_list_item_includes_template_id(client_with_run_store):
    client, store = client_with_run_store
    _create_run_with_template(store, template_id="ops_review")
    resp = client.get("/v1/runs")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["template_id"] == "ops_review"


def test_run_list_filter_by_template_id_via_list_runs(client_with_run_store):
    """list_runs filters don't include template_id filter — that's list_runs_by_template.
    But template_id is present in each item."""
    client, store = client_with_run_store
    _create_run_with_template(store, run_id="run-a", template_id="exec_brief")
    _create_run_with_template(store, run_id="run-b", template_id="arch_overview")
    resp = client.get("/v1/runs")
    assert resp.status_code == 200
    items = resp.json()["runs"]
    template_ids = {r["template_id"] for r in items}
    assert "exec_brief" in template_ids
    assert "arch_overview" in template_ids


# ---------------------------------------------------------------------------
# Template fields round-trip through SQLite
# ---------------------------------------------------------------------------

def test_template_version_roundtrips_through_sqlite(tmp_path):
    db = tmp_path / "runs.db"
    store = SQLiteRunStore(db_path=db)
    run = RunRecord.create(
        source=RunSource.API_SYNC,
        run_id="run-rt-001",
        template_id="exec_brief",
        template_version="3.1.4",
        template_revision_hash="1234abcd5678ef90",
    )
    store.create(run)
    retrieved = store.get("run-rt-001")
    assert retrieved is not None
    assert retrieved.template_id == "exec_brief"
    assert retrieved.template_version == "3.1.4"
    assert retrieved.template_revision_hash == "1234abcd5678ef90"
    store.close()


def test_template_fields_survive_migration(tmp_path):
    """Old DB without template columns gets migrated; new runs can store template data."""
    import sqlite3
    db_path = tmp_path / "old.db"
    # Create a minimal DB without the new columns (simulating pre-Stage-1 schema)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE runs (
        run_id TEXT PRIMARY KEY, status TEXT NOT NULL, source TEXT NOT NULL,
        job_id TEXT, request_id TEXT, mode TEXT NOT NULL DEFAULT 'deterministic',
        template_id TEXT, playbook_id TEXT, profile TEXT NOT NULL DEFAULT 'dev',
        config_fingerprint TEXT, started_at TEXT NOT NULL, completed_at TEXT,
        total_ms REAL, error_category TEXT, error_message TEXT, manifest_path TEXT
    )""")
    conn.execute(
        "INSERT INTO runs (run_id, status, source, started_at) VALUES (?,?,?,?)",
        ("old-run-001", "succeeded", "api_sync", "2026-01-01T00:00:00"),
    )
    conn.commit()
    conn.close()

    # Opening with SQLiteRunStore should migrate and allow new data
    store = SQLiteRunStore(db_path=db_path)
    run = RunRecord.create(
        source=RunSource.API_SYNC,
        run_id="new-run-001",
        template_version="1.0.0",
        template_revision_hash="ab12cd34ef56ab12",
    )
    store.create(run)
    retrieved = store.get("new-run-001")
    assert retrieved.template_version == "1.0.0"

    # Old run has None for new fields
    old = store.get("old-run-001")
    assert old.template_version is None
    assert old.template_revision_hash is None
    store.close()
