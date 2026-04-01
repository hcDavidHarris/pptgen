"""Tests for list_runs_by_template — Phase 8 Stage 2."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore
from pptgen.templates.models import Template, TemplateVersion
from pptgen.templates.registry import VersionedTemplateRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run(
    run_id: str,
    template_id: str | None = "exec_brief",
    template_version: str | None = "1.0.0",
    status: RunStatus = RunStatus.SUCCEEDED,
    started_at: datetime | None = None,
) -> RunRecord:
    run = RunRecord.create(
        source=RunSource.API_SYNC,
        run_id=run_id,
        template_id=template_id,
        template_version=template_version,
    )
    run.status = status
    if started_at:
        run.started_at = started_at
    return run


def _make_registry(*template_ids: str) -> VersionedTemplateRegistry:
    templates = []
    for tid in template_ids:
        ver = TemplateVersion(
            version_id=f"vid-{tid}",
            template_id=tid,
            version="1.0.0",
            template_revision_hash="ab12cd34ef56ab12",
        )
        templates.append(Template(
            template_id=tid,
            template_key=tid,
            name=tid.replace("_", " ").title(),
            lifecycle_status="approved",
            versions=[ver],
        ))
    return VersionedTemplateRegistry(templates)


# ---------------------------------------------------------------------------
# SQLiteRunStore.list_runs_by_template unit tests
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    db = tmp_path / "runs.db"
    s = SQLiteRunStore(db_path=db)
    yield s
    s.close()


def test_list_runs_by_template_empty(store):
    result = store.list_runs_by_template("exec_brief")
    assert result == []


def test_list_runs_by_template_returns_matching(store):
    run = _make_run("run-001", template_id="exec_brief")
    store.create(run)
    result = store.list_runs_by_template("exec_brief")
    assert len(result) == 1
    assert result[0].run_id == "run-001"


def test_list_runs_by_template_excludes_others(store):
    store.create(_make_run("run-001", template_id="exec_brief"))
    store.create(_make_run("run-002", template_id="arch_overview"))
    result = store.list_runs_by_template("exec_brief")
    assert len(result) == 1
    assert result[0].run_id == "run-001"


def test_list_runs_by_template_filter_version(store):
    store.create(_make_run("run-001", template_id="tmpl", template_version="1.0.0"))
    store.create(_make_run("run-002", template_id="tmpl", template_version="2.0.0"))
    result = store.list_runs_by_template("tmpl", template_version="1.0.0")
    assert len(result) == 1
    assert result[0].run_id == "run-001"


def test_list_runs_by_template_filter_status(store):
    store.create(_make_run("run-001", status=RunStatus.SUCCEEDED))
    store.create(_make_run("run-002", status=RunStatus.FAILED))
    result = store.list_runs_by_template("exec_brief", status="succeeded")
    assert len(result) == 1
    assert result[0].run_id == "run-001"


def test_list_runs_by_template_filter_since_iso(store):
    now = datetime.now(tz=timezone.utc)
    old = _make_run("run-old", started_at=now - timedelta(days=60))
    recent = _make_run("run-new", started_at=now - timedelta(days=1))
    store.create(old)
    store.create(recent)
    since = (now - timedelta(days=30)).isoformat()
    result = store.list_runs_by_template("exec_brief", since_iso=since)
    assert len(result) == 1
    assert result[0].run_id == "run-new"


def test_list_runs_by_template_pagination(store):
    for i in range(5):
        store.create(_make_run(f"run-{i:03d}"))
    page1 = store.list_runs_by_template("exec_brief", limit=2, offset=0)
    page2 = store.list_runs_by_template("exec_brief", limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    ids_p1 = {r.run_id for r in page1}
    ids_p2 = {r.run_id for r in page2}
    assert ids_p1.isdisjoint(ids_p2)


def test_list_runs_by_template_no_template_id_match(store):
    store.create(_make_run("run-001", template_id=None))
    result = store.list_runs_by_template("exec_brief")
    assert result == []


def test_list_runs_by_template_preserves_template_version(store):
    run = _make_run("run-001", template_id="tmpl", template_version="2.3.1")
    store.create(run)
    result = store.list_runs_by_template("tmpl")
    assert result[0].template_version == "2.3.1"


# ---------------------------------------------------------------------------
# API endpoint: GET /v1/templates/{template_id}/runs
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client(tmp_path):
    db = tmp_path / "artifacts.db"
    run_store = SQLiteRunStore(db_path=db)
    artifact_store = SQLiteArtifactStore(db_path=db)
    artifact_storage = ArtifactStorage(base=tmp_path / "store")
    registry = _make_registry("exec_brief", "arch_overview")

    app.state.run_store = run_store
    app.state.artifact_store = artifact_store
    app.state.artifact_storage = artifact_storage
    app.state.template_registry = registry

    client = TestClient(app, raise_server_exceptions=False)
    yield client, run_store
    run_store.close()
    artifact_store.close()
    app.state.run_store = None
    app.state.artifact_store = None
    app.state.template_registry = None


def test_api_template_runs_empty(api_client):
    client, _ = api_client
    resp = client.get("/v1/templates/exec_brief/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == "exec_brief"
    assert data["runs"] == []
    assert data["total"] == 0


def test_api_template_runs_returns_runs(api_client):
    client, store = api_client
    store.create(_make_run("run-001", template_id="exec_brief", template_version="1.0.0"))
    resp = client.get("/v1/templates/exec_brief/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["runs"]) == 1
    run = data["runs"][0]
    assert run["run_id"] == "run-001"
    assert run["template_version"] == "1.0.0"
    assert "status" in run
    assert "started_at" in run


def test_api_template_runs_404_for_unknown_template(api_client):
    client, _ = api_client
    resp = client.get("/v1/templates/nonexistent/runs")
    assert resp.status_code == 404


def test_api_template_runs_503_no_registry(tmp_path):
    db = tmp_path / "artifacts.db"
    run_store = SQLiteRunStore(db_path=db)
    app.state.run_store = run_store
    app.state.template_registry = None
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/v1/templates/exec_brief/runs")
    assert resp.status_code == 503
    run_store.close()
    app.state.run_store = None


def test_api_template_runs_503_no_run_store(tmp_path):
    registry = _make_registry("exec_brief")
    app.state.run_store = None
    app.state.template_registry = registry
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/v1/templates/exec_brief/runs")
    assert resp.status_code == 503
    app.state.template_registry = None


def test_api_template_runs_filter_version(api_client):
    client, store = api_client
    store.create(_make_run("run-001", template_id="exec_brief", template_version="1.0.0"))
    store.create(_make_run("run-002", template_id="exec_brief", template_version="2.0.0"))
    resp = client.get("/v1/templates/exec_brief/runs?template_version=1.0.0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["runs"]) == 1
    assert data["runs"][0]["run_id"] == "run-001"


def test_api_template_runs_filter_status(api_client):
    client, store = api_client
    store.create(_make_run("run-ok", status=RunStatus.SUCCEEDED))
    store.create(_make_run("run-fail", status=RunStatus.FAILED))
    resp = client.get("/v1/templates/exec_brief/runs?status=succeeded")
    assert resp.status_code == 200
    ids = [r["run_id"] for r in resp.json()["runs"]]
    assert "run-ok" in ids
    assert "run-fail" not in ids


def test_api_template_runs_days_filter(api_client):
    client, store = api_client
    now = datetime.now(tz=timezone.utc)
    old = _make_run("run-old", started_at=now - timedelta(days=60))
    recent = _make_run("run-new", started_at=now - timedelta(days=1))
    store.create(old)
    store.create(recent)
    resp = client.get("/v1/templates/exec_brief/runs?days=30")
    assert resp.status_code == 200
    ids = [r["run_id"] for r in resp.json()["runs"]]
    assert "run-new" in ids
    assert "run-old" not in ids


def test_api_template_runs_pagination(api_client):
    client, store = api_client
    for i in range(5):
        store.create(_make_run(f"run-{i:03d}"))
    resp1 = client.get("/v1/templates/exec_brief/runs?limit=2&offset=0")
    resp2 = client.get("/v1/templates/exec_brief/runs?limit=2&offset=2")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    ids1 = {r["run_id"] for r in resp1.json()["runs"]}
    ids2 = {r["run_id"] for r in resp2.json()["runs"]}
    assert ids1.isdisjoint(ids2)
