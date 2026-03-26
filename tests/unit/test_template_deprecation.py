"""Tests for POST /v1/templates/{id}/versions/{version}/deprecate — Phase 8 Stage 3."""
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
        _make_template("solo_tmpl", lifecycle_status="approved", versions=["1.0.0"]),
    ])
    app.state.template_registry = reg
    app.state.governance_store = gov
    client = TestClient(app, raise_server_exceptions=False)
    yield client, gov
    app.state.template_registry = None
    app.state.governance_store = None


# ---------------------------------------------------------------------------
# POST /v1/templates/{id}/versions/{version}/deprecate — happy path
# ---------------------------------------------------------------------------

def test_deprecate_version_ok(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "superseded by 2.0.0", "actor": "alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == "exec_brief"
    assert data["version"] == "1.0.0"
    assert data["action"] == "deprecated"
    assert data["accepted"] is True


def test_deprecate_marks_version_in_store(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "old"},
    )
    assert gov.is_deprecated("exec_brief", "1.0.0") is True


def test_deprecate_does_not_affect_other_versions(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "old"},
    )
    assert gov.is_deprecated("exec_brief", "2.0.0") is False


def test_deprecate_writes_audit_event(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "superseded", "actor": "bob"},
    )
    events = gov.list_audit_events(template_id="exec_brief")
    dep_events = [e for e in events if e["event_type"] == "template_version_deprecated"]
    assert len(dep_events) == 1
    assert dep_events[0]["actor"] == "bob"
    assert dep_events[0]["reason"] == "superseded"


def test_deprecate_requires_reason_field(client_with_gov):
    """reason is required by DeprecateVersionRequest schema."""
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={},  # missing reason
    )
    assert resp.status_code == 422


def test_deprecate_clears_default_if_was_default(client_with_gov):
    """Deprecating the current default version clears the explicit default pin."""
    client, gov = client_with_gov
    gov.set_default_version("exec_brief", "1.0.0")
    client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "bad release"},
    )
    assert gov.get_default_version("exec_brief") is None


def test_deprecate_non_default_leaves_default_untouched(client_with_gov):
    client, gov = client_with_gov
    gov.set_default_version("exec_brief", "2.0.0")
    client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "old"},
    )
    assert gov.get_default_version("exec_brief") == "2.0.0"


# ---------------------------------------------------------------------------
# POST /v1/templates/{id}/versions/{version}/deprecate — error cases
# ---------------------------------------------------------------------------

def test_deprecate_unknown_template_returns_422(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/nonexistent/versions/1.0.0/deprecate",
        json={"reason": "test"},
    )
    assert resp.status_code == 422


def test_deprecate_unknown_version_returns_422(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/exec_brief/versions/9.9.9/deprecate",
        json={"reason": "test"},
    )
    assert resp.status_code == 422


def test_deprecate_already_deprecated_returns_422(client_with_gov):
    client, gov = client_with_gov
    gov.deprecate_version("exec_brief", "1.0.0", reason="old")
    resp = client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "again"},
    )
    assert resp.status_code == 422
    assert "already deprecated" in resp.json()["detail"].lower()


def test_deprecate_sole_version_returns_422(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/solo_tmpl/versions/1.0.0/deprecate",
        json={"reason": "removing"},
    )
    assert resp.status_code == 422
    assert "only non-deprecated" in resp.json()["detail"].lower()


def test_deprecate_no_governance_store_returns_503(tmp_path):
    reg = VersionedTemplateRegistry([
        _make_template("exec_brief", versions=["1.0.0", "2.0.0"]),
    ])
    app.state.template_registry = reg
    app.state.governance_store = None
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "test"},
    )
    assert resp.status_code == 503
    app.state.template_registry = None


# ---------------------------------------------------------------------------
# GET /v1/templates/{id}/versions reflects governance state after deprecate
# ---------------------------------------------------------------------------

def test_versions_endpoint_shows_deprecated_at_after_deprecate(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "old"},
    )
    resp = client.get("/v1/templates/exec_brief/versions")
    assert resp.status_code == 200
    by_version = {v["version"]: v for v in resp.json()}
    assert by_version["1.0.0"]["deprecated_at"] is not None
    assert by_version["1.0.0"]["deprecation_reason"] == "old"
    assert by_version["2.0.0"]["deprecated_at"] is None


def test_governance_endpoint_shows_deprecated_versions(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "old"},
    )
    resp = client.get("/v1/templates/exec_brief/governance")
    assert resp.status_code == 200
    assert "1.0.0" in resp.json()["deprecated_versions"]
    assert "2.0.0" not in resp.json()["deprecated_versions"]


# ---------------------------------------------------------------------------
# Audit trail accumulates across multiple governance actions
# ---------------------------------------------------------------------------

def test_audit_trail_accumulates_multiple_actions(client_with_gov):
    client, gov = client_with_gov
    client.post("/v1/templates/exec_brief/versions/2.0.0/promote", json={"actor": "alice"})
    client.post(
        "/v1/templates/exec_brief/versions/1.0.0/deprecate",
        json={"reason": "superseded", "actor": "bob"},
    )
    resp = client.get("/v1/templates/exec_brief/governance/audit")
    assert resp.status_code == 200
    events = resp.json()
    event_types = {e["event_type"] for e in events}
    assert "template_version_promoted" in event_types
    assert "template_version_deprecated" in event_types
