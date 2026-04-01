"""Tests for template usage analytics — Phase 8 Analytics.

Covers:
- SQLiteRunStore.get_template_usage_summary — totals, failure rate, days filter, zero runs
- SQLiteRunStore.get_template_version_usage — per-version aggregates, mixed statuses
- SQLiteRunStore.get_template_usage_trend — daily counts per version
- GET /v1/templates/{id}/analytics/summary
- GET /v1/templates/{id}/analytics/versions
- GET /v1/templates/{id}/analytics/trend
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore
from pptgen.templates.models import Template, TemplateVersion
from pptgen.templates.registry import VersionedTemplateRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run(
    template_id: str,
    template_version: str,
    status: str = "succeeded",
    days_ago: float = 1.0,
) -> RunRecord:
    started = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    completed = started + timedelta(seconds=5)
    r = RunRecord.create(source=RunSource.API_SYNC)
    r = r.__class__(
        run_id=r.run_id,
        status=RunStatus(status),
        source=RunSource.API_SYNC,
        template_id=template_id,
        template_version=template_version,
        template_revision_hash="abc123def456ab12",
        started_at=started,
        completed_at=completed,
        total_ms=5000.0,
    )
    return r


@pytest.fixture
def store(tmp_path):
    s = SQLiteRunStore(tmp_path / "runs.db")
    yield s
    s.close()


def _seed(store: SQLiteRunStore, runs: list[RunRecord]) -> None:
    for r in runs:
        store.create(r)
        store.update_status(r.run_id, r.status, total_ms=r.total_ms)


# ---------------------------------------------------------------------------
# get_template_usage_summary — unit tests
# ---------------------------------------------------------------------------

def test_summary_empty_template(store):
    result = store.get_template_usage_summary("no_such_tmpl")
    assert result["total_runs"] == 0
    assert result["completed_runs"] == 0
    assert result["failed_runs"] == 0
    assert result["cancelled_runs"] == 0
    assert result["failure_rate"] is None


def test_summary_all_succeeded(store):
    _seed(store, [_make_run("tmpl", "1.0.0", "succeeded") for _ in range(5)])
    result = store.get_template_usage_summary("tmpl")
    assert result["total_runs"] == 5
    assert result["completed_runs"] == 5
    assert result["failed_runs"] == 0
    assert result["failure_rate"] == 0.0


def test_summary_mixed_statuses(store):
    runs = [
        _make_run("tmpl", "1.0.0", "succeeded"),
        _make_run("tmpl", "1.0.0", "succeeded"),
        _make_run("tmpl", "1.0.0", "failed"),
        _make_run("tmpl", "1.0.0", "cancelled"),
    ]
    _seed(store, runs)
    result = store.get_template_usage_summary("tmpl")
    assert result["total_runs"] == 4
    assert result["completed_runs"] == 2
    assert result["failed_runs"] == 1
    assert result["cancelled_runs"] == 1
    assert result["failure_rate"] == pytest.approx(0.25)


def test_summary_failure_rate_all_failed(store):
    _seed(store, [_make_run("tmpl", "1.0.0", "failed") for _ in range(3)])
    result = store.get_template_usage_summary("tmpl")
    assert result["failure_rate"] == pytest.approx(1.0)


def test_summary_days_filter_excludes_old_runs(store):
    old = _make_run("tmpl", "1.0.0", "succeeded", days_ago=40)
    recent = _make_run("tmpl", "1.0.0", "failed", days_ago=5)
    _seed(store, [old, recent])
    result = store.get_template_usage_summary("tmpl", days=30)
    assert result["total_runs"] == 1
    assert result["failed_runs"] == 1


def test_summary_days_filter_includes_all_in_window(store):
    runs = [_make_run("tmpl", "1.0.0", "succeeded", days_ago=i) for i in range(1, 6)]
    _seed(store, runs)
    result = store.get_template_usage_summary("tmpl", days=30)
    assert result["total_runs"] == 5


def test_summary_does_not_mix_templates(store):
    _seed(store, [_make_run("tmpl_a", "1.0.0", "succeeded")])
    _seed(store, [_make_run("tmpl_b", "1.0.0", "failed")])
    result_a = store.get_template_usage_summary("tmpl_a")
    assert result_a["total_runs"] == 1
    assert result_a["failed_runs"] == 0


def test_summary_template_id_in_response(store):
    result = store.get_template_usage_summary("my_tmpl")
    assert result["template_id"] == "my_tmpl"
    assert result["date_window_days"] == 30


# ---------------------------------------------------------------------------
# get_template_version_usage — unit tests
# ---------------------------------------------------------------------------

def test_version_usage_empty(store):
    result = store.get_template_version_usage("no_such_tmpl")
    assert result == []


def test_version_usage_single_version(store):
    _seed(store, [_make_run("tmpl", "1.0.0", "succeeded") for _ in range(3)])
    result = store.get_template_version_usage("tmpl")
    assert len(result) == 1
    row = result[0]
    assert row["template_version"] == "1.0.0"
    assert row["total_runs"] == 3
    assert row["failed_runs"] == 0
    assert row["failure_rate"] == 0.0


def test_version_usage_multiple_versions(store):
    _seed(store, [
        _make_run("tmpl", "1.0.0", "succeeded"),
        _make_run("tmpl", "1.0.0", "failed"),
        _make_run("tmpl", "2.0.0", "succeeded"),
        _make_run("tmpl", "2.0.0", "succeeded"),
        _make_run("tmpl", "2.0.0", "succeeded"),
    ])
    result = store.get_template_version_usage("tmpl")
    by_ver = {r["template_version"]: r for r in result}
    assert by_ver["1.0.0"]["total_runs"] == 2
    assert by_ver["1.0.0"]["failed_runs"] == 1
    assert by_ver["1.0.0"]["failure_rate"] == pytest.approx(0.5)
    assert by_ver["2.0.0"]["total_runs"] == 3
    assert by_ver["2.0.0"]["failed_runs"] == 0


def test_version_usage_sorted_by_total_runs_desc(store):
    _seed(store, [_make_run("tmpl", "1.0.0")] + [_make_run("tmpl", "2.0.0") for _ in range(5)])
    result = store.get_template_version_usage("tmpl")
    assert result[0]["template_version"] == "2.0.0"


def test_version_usage_excludes_null_version(store):
    # Run without template_version set — should not appear in version usage
    r = RunRecord.create(source=RunSource.API_SYNC)
    r = r.__class__(run_id=r.run_id, status=RunStatus.SUCCEEDED, source=RunSource.API_SYNC,
                    template_id="tmpl", template_version=None, started_at=datetime.now(tz=timezone.utc))
    store.create(r)
    result = store.get_template_version_usage("tmpl")
    assert result == []


def test_version_usage_includes_first_and_last_seen(store):
    old = _make_run("tmpl", "1.0.0", "succeeded", days_ago=10)
    new = _make_run("tmpl", "1.0.0", "succeeded", days_ago=1)
    _seed(store, [old, new])
    result = store.get_template_version_usage("tmpl")
    row = result[0]
    assert row["first_seen_at"] is not None
    assert row["last_seen_at"] is not None
    assert row["first_seen_at"] < row["last_seen_at"]


def test_version_usage_days_filter(store):
    old = _make_run("tmpl", "1.0.0", "succeeded", days_ago=45)
    recent = _make_run("tmpl", "2.0.0", "succeeded", days_ago=5)
    _seed(store, [old, recent])
    result = store.get_template_version_usage("tmpl", days=30)
    versions = [r["template_version"] for r in result]
    assert "2.0.0" in versions
    assert "1.0.0" not in versions


# ---------------------------------------------------------------------------
# get_template_usage_trend — unit tests
# ---------------------------------------------------------------------------

def test_trend_empty(store):
    result = store.get_template_usage_trend("no_such_tmpl")
    assert result == []


def test_trend_single_day_single_version(store):
    _seed(store, [_make_run("tmpl", "1.0.0", "succeeded", days_ago=1) for _ in range(3)])
    result = store.get_template_usage_trend("tmpl")
    assert len(result) == 1
    assert result[0]["template_version"] == "1.0.0"
    assert result[0]["run_count"] == 3
    assert result[0]["date"] is not None


def test_trend_multiple_versions_same_day(store):
    _seed(store, [
        _make_run("tmpl", "1.0.0", "succeeded", days_ago=1),
        _make_run("tmpl", "2.0.0", "succeeded", days_ago=1),
        _make_run("tmpl", "2.0.0", "succeeded", days_ago=1),
    ])
    result = store.get_template_usage_trend("tmpl")
    by_ver = {r["template_version"]: r for r in result}
    assert by_ver["1.0.0"]["run_count"] == 1
    assert by_ver["2.0.0"]["run_count"] == 2


def test_trend_days_filter(store):
    old = _make_run("tmpl", "1.0.0", "succeeded", days_ago=45)
    recent = _make_run("tmpl", "2.0.0", "succeeded", days_ago=5)
    _seed(store, [old, recent])
    result = store.get_template_usage_trend("tmpl", days=30)
    assert all(r["template_version"] == "2.0.0" for r in result)


def test_trend_excludes_null_version(store):
    r = RunRecord.create(source=RunSource.API_SYNC)
    r = r.__class__(run_id=r.run_id, status=RunStatus.SUCCEEDED, source=RunSource.API_SYNC,
                    template_id="tmpl", template_version=None, started_at=datetime.now(tz=timezone.utc))
    store.create(r)
    result = store.get_template_usage_trend("tmpl")
    assert result == []


def test_trend_ordered_by_date_asc(store):
    _seed(store, [
        _make_run("tmpl", "1.0.0", "succeeded", days_ago=5),
        _make_run("tmpl", "1.0.0", "succeeded", days_ago=3),
        _make_run("tmpl", "1.0.0", "succeeded", days_ago=1),
    ])
    result = store.get_template_usage_trend("tmpl")
    dates = [r["date"] for r in result]
    assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

def _make_version(template_id: str, version: str) -> TemplateVersion:
    return TemplateVersion(
        version_id=f"vid-{template_id}-{version}",
        template_id=template_id,
        version=version,
        template_revision_hash="abc123def456ab12",
    )


def _make_template(template_id: str, versions: list[str] | None = None) -> Template:
    vers = [_make_version(template_id, v) for v in (versions or ["1.0.0"])]
    return Template(
        template_id=template_id,
        template_key=template_id,
        name=template_id,
        lifecycle_status="approved",
        versions=vers,
    )


@pytest.fixture
def api_client(tmp_path):
    store = SQLiteRunStore(tmp_path / "runs.db")
    reg = VersionedTemplateRegistry([
        _make_template("exec_brief", versions=["1.0.0", "2.0.0"]),
    ])
    app.state.template_registry = reg
    app.state.run_store = store
    app.state.governance_store = None
    client = TestClient(app, raise_server_exceptions=False)
    yield client, store
    store.close()
    app.state.template_registry = None
    app.state.run_store = None


def test_analytics_summary_empty(api_client):
    client, store = api_client
    resp = client.get("/v1/templates/exec_brief/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == "exec_brief"
    assert data["total_runs"] == 0
    assert data["failure_rate"] is None


def test_analytics_summary_with_data(api_client):
    client, store = api_client
    _seed(store, [
        _make_run("exec_brief", "2.0.0", "succeeded"),
        _make_run("exec_brief", "2.0.0", "succeeded"),
        _make_run("exec_brief", "2.0.0", "failed"),
    ])
    resp = client.get("/v1/templates/exec_brief/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] == 3
    assert data["failed_runs"] == 1
    assert data["failure_rate"] == pytest.approx(1 / 3, rel=1e-3)


def test_analytics_summary_not_found(api_client):
    client, _ = api_client
    resp = client.get("/v1/templates/nonexistent/analytics/summary")
    assert resp.status_code == 404


def test_analytics_summary_days_param(api_client):
    client, store = api_client
    _seed(store, [
        _make_run("exec_brief", "1.0.0", "succeeded", days_ago=5),
        _make_run("exec_brief", "1.0.0", "failed", days_ago=40),
    ])
    resp = client.get("/v1/templates/exec_brief/analytics/summary?days=30")
    assert resp.json()["total_runs"] == 1


def test_analytics_versions_empty(api_client):
    client, _ = api_client
    resp = client.get("/v1/templates/exec_brief/analytics/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["versions"] == []


def test_analytics_versions_with_data(api_client):
    client, store = api_client
    _seed(store, [
        _make_run("exec_brief", "1.0.0", "succeeded"),
        _make_run("exec_brief", "2.0.0", "succeeded"),
        _make_run("exec_brief", "2.0.0", "failed"),
    ])
    resp = client.get("/v1/templates/exec_brief/analytics/versions")
    assert resp.status_code == 200
    data = resp.json()
    by_ver = {v["template_version"]: v for v in data["versions"]}
    assert "1.0.0" in by_ver
    assert "2.0.0" in by_ver
    assert by_ver["2.0.0"]["failed_runs"] == 1


def test_analytics_versions_not_found(api_client):
    client, _ = api_client
    resp = client.get("/v1/templates/nonexistent/analytics/versions")
    assert resp.status_code == 404


def test_analytics_trend_empty(api_client):
    client, _ = api_client
    resp = client.get("/v1/templates/exec_brief/analytics/trend")
    assert resp.status_code == 200
    assert resp.json()["trend"] == []


def test_analytics_trend_with_data(api_client):
    client, store = api_client
    _seed(store, [
        _make_run("exec_brief", "1.0.0", "succeeded", days_ago=5),
        _make_run("exec_brief", "2.0.0", "succeeded", days_ago=5),
        _make_run("exec_brief", "2.0.0", "succeeded", days_ago=1),
    ])
    resp = client.get("/v1/templates/exec_brief/analytics/trend")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["trend"]) >= 2  # at least 2 (version×day) combos


def test_analytics_trend_not_found(api_client):
    client, _ = api_client
    resp = client.get("/v1/templates/nonexistent/analytics/trend")
    assert resp.status_code == 404


def test_analytics_trend_days_param(api_client):
    client, store = api_client
    _seed(store, [
        _make_run("exec_brief", "1.0.0", "succeeded", days_ago=5),
        _make_run("exec_brief", "2.0.0", "succeeded", days_ago=40),
    ])
    resp = client.get("/v1/templates/exec_brief/analytics/trend?days=30")
    data = resp.json()
    versions_in_trend = {t["template_version"] for t in data["trend"]}
    assert "1.0.0" in versions_in_trend
    assert "2.0.0" not in versions_in_trend
