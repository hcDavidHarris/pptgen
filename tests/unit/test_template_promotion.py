"""Tests for POST /v1/templates/{id}/versions/{version}/promote — Phase 8 Stage 3."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.templates.governance import GovernanceStore
from pptgen.templates.models import Template, TemplateVersion
from pptgen.templates.registry import VersionedTemplateRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_version(template_id: str, version: str) -> TemplateVersion:
    return TemplateVersion(
        version_id=f"vid-{template_id}-{version}",
        template_id=template_id,
        version=version,
        template_revision_hash="abc123def456ab12",
    )


def _make_template(
    template_id: str,
    lifecycle_status: str = "approved",
    versions: list[str] | None = None,
) -> Template:
    vers = [_make_version(template_id, v) for v in (versions or ["1.0.0"])]
    return Template(
        template_id=template_id,
        template_key=template_id,
        name=template_id.replace("_", " ").title(),
        lifecycle_status=lifecycle_status,
        versions=vers,
    )


@pytest.fixture
def gov(tmp_path):
    store = GovernanceStore(tmp_path / "gov.db")
    yield store
    store.close()


@pytest.fixture
def client_with_gov(gov):
    reg = VersionedTemplateRegistry([
        _make_template("exec_brief", lifecycle_status="approved", versions=["1.0.0", "2.0.0"]),
        _make_template("draft_tmpl", lifecycle_status="draft", versions=["0.1.0"]),
    ])
    app.state.template_registry = reg
    app.state.governance_store = gov
    client = TestClient(app, raise_server_exceptions=False)
    yield client, gov
    app.state.template_registry = None
    app.state.governance_store = None


# ---------------------------------------------------------------------------
# POST /v1/templates/{id}/versions/{version}/promote — happy path
# ---------------------------------------------------------------------------

def test_promote_version_ok(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/exec_brief/versions/2.0.0/promote",
        json={"actor": "alice", "reason": "stable release"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == "exec_brief"
    assert data["version"] == "2.0.0"
    assert data["action"] == "promoted"
    assert data["accepted"] is True
    assert "2.0.0" in data["message"]


def test_promote_sets_default_in_governance_store(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/exec_brief/versions/2.0.0/promote",
        json={"actor": "alice"},
    )
    assert gov.get_default_version("exec_brief") == "2.0.0"


def test_promote_returns_previous_default(client_with_gov):
    client, gov = client_with_gov
    # First promote 1.0.0
    client.post("/v1/templates/exec_brief/versions/1.0.0/promote", json={})
    # Now promote 2.0.0 — previous_default should be 1.0.0
    resp = client.post("/v1/templates/exec_brief/versions/2.0.0/promote", json={})
    assert resp.status_code == 200
    assert resp.json()["previous_default"] == "1.0.0"


def test_promote_no_previous_default_returns_null(client_with_gov):
    client, gov = client_with_gov
    resp = client.post("/v1/templates/exec_brief/versions/1.0.0/promote", json={})
    assert resp.status_code == 200
    assert resp.json()["previous_default"] is None


def test_promote_clears_previous_default(client_with_gov):
    client, gov = client_with_gov
    client.post("/v1/templates/exec_brief/versions/1.0.0/promote", json={})
    client.post("/v1/templates/exec_brief/versions/2.0.0/promote", json={})
    assert gov.get_default_version("exec_brief") == "2.0.0"


def test_promote_writes_audit_event(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/exec_brief/versions/2.0.0/promote",
        json={"actor": "bob", "reason": "v2 ready"},
    )
    events = gov.list_audit_events(template_id="exec_brief")
    assert len(events) >= 1
    promote_events = [e for e in events if e["event_type"] == "template_version_promoted"]
    assert len(promote_events) == 1
    assert promote_events[0]["actor"] == "bob"
    assert promote_events[0]["reason"] == "v2 ready"


def test_promote_records_promotion_timestamp(client_with_gov):
    client, gov = client_with_gov
    client.post("/v1/templates/exec_brief/versions/2.0.0/promote", json={})
    ts = gov.get_promotion_timestamp("exec_brief", "2.0.0")
    assert ts is not None


# ---------------------------------------------------------------------------
# POST /v1/templates/{id}/versions/{version}/promote — error cases
# ---------------------------------------------------------------------------

def test_promote_unknown_template_returns_503_or_422(client_with_gov):
    """Promoting a non-existent template returns 422 (validation error)."""
    client, gov = client_with_gov
    resp = client.post("/v1/templates/nonexistent/versions/1.0.0/promote", json={})
    assert resp.status_code == 422


def test_promote_unknown_version_returns_422(client_with_gov):
    client, gov = client_with_gov
    resp = client.post("/v1/templates/exec_brief/versions/9.9.9/promote", json={})
    assert resp.status_code == 422


def test_promote_deprecated_version_returns_422(client_with_gov):
    client, gov = client_with_gov
    gov.deprecate_version("exec_brief", "1.0.0", reason="old")
    resp = client.post("/v1/templates/exec_brief/versions/1.0.0/promote", json={})
    assert resp.status_code == 422
    assert "deprecated" in resp.json()["detail"].lower()


def test_promote_no_governance_store_returns_503(tmp_path):
    reg = VersionedTemplateRegistry([
        _make_template("exec_brief", versions=["1.0.0"]),
    ])
    app.state.template_registry = reg
    app.state.governance_store = None
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/v1/templates/exec_brief/versions/1.0.0/promote", json={})
    assert resp.status_code == 503
    app.state.template_registry = None


# ---------------------------------------------------------------------------
# GET /v1/templates/{id}/versions reflects governance state after promote
# ---------------------------------------------------------------------------

def test_versions_endpoint_shows_is_default_after_promote(client_with_gov):
    client, gov = client_with_gov
    client.post("/v1/templates/exec_brief/versions/2.0.0/promote", json={})
    resp = client.get("/v1/templates/exec_brief/versions")
    assert resp.status_code == 200
    by_version = {v["version"]: v for v in resp.json()}
    assert by_version["2.0.0"]["is_default"] is True
    assert by_version["1.0.0"]["is_default"] is False


def test_versions_endpoint_shows_promotion_timestamp(client_with_gov):
    client, gov = client_with_gov
    client.post("/v1/templates/exec_brief/versions/2.0.0/promote", json={})
    resp = client.get("/v1/templates/exec_brief/versions")
    by_version = {v["version"]: v for v in resp.json()}
    assert by_version["2.0.0"]["promotion_timestamp"] is not None


# ---------------------------------------------------------------------------
# GET /v1/templates/{id}/governance reflects default after promote
# ---------------------------------------------------------------------------

def test_governance_endpoint_shows_default_after_promote(client_with_gov):
    client, gov = client_with_gov
    client.post("/v1/templates/exec_brief/versions/2.0.0/promote", json={})
    resp = client.get("/v1/templates/exec_brief/governance")
    assert resp.status_code == 200
    assert resp.json()["default_version"] == "2.0.0"
