"""Tests for lifecycle enforcement in resolution + API — Phase 8 Stage 3.

Covers:
- POST /v1/templates/{id}/lifecycle (change lifecycle, validate transition, audit)
- GET /v1/templates/{id}/governance (effective lifecycle + governance state)
- GET /v1/templates/{id}/governance/audit (audit trail for lifecycle events)
- resolve_template_for_run with governance: lifecycle block, deprecated version block
- resolve_template_for_replay: ignores lifecycle/deprecation enforcement
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.templates.governance import GovernanceStore
from pptgen.templates.models import Template, TemplateVersion
from pptgen.templates.registry import VersionedTemplateRegistry
from pptgen.templates.resolution import resolve_template_for_replay, resolve_template_for_run


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
def reg():
    return VersionedTemplateRegistry([
        _make_template("approved_tmpl", lifecycle_status="approved", versions=["1.0.0", "2.0.0"]),
        _make_template("draft_tmpl", lifecycle_status="draft", versions=["0.1.0"]),
        _make_template("deprecated_tmpl", lifecycle_status="deprecated", versions=["1.0.0"]),
        _make_template("review_tmpl", lifecycle_status="review", versions=["1.0.0"]),
    ])


@pytest.fixture
def client_with_gov(gov, reg):
    app.state.template_registry = reg
    app.state.governance_store = gov
    client = TestClient(app, raise_server_exceptions=False)
    yield client, gov
    app.state.template_registry = None
    app.state.governance_store = None


# ---------------------------------------------------------------------------
# POST /v1/templates/{id}/lifecycle — happy path
# ---------------------------------------------------------------------------

def test_lifecycle_change_ok(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/approved_tmpl/lifecycle",
        json={"lifecycle_status": "deprecated", "actor": "alice", "reason": "retiring"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == "approved_tmpl"
    assert data["action"] == "lifecycle_changed"
    assert data["accepted"] is True
    assert "deprecated" in data["message"]


def test_lifecycle_change_persists_in_store(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/approved_tmpl/lifecycle",
        json={"lifecycle_status": "deprecated"},
    )
    assert gov.get_lifecycle("approved_tmpl") == "deprecated"


def test_lifecycle_change_writes_audit_event(client_with_gov):
    client, gov = client_with_gov
    client.post(
        "/v1/templates/approved_tmpl/lifecycle",
        json={"lifecycle_status": "deprecated", "actor": "carol", "reason": "EOL"},
    )
    events = gov.list_audit_events(template_id="approved_tmpl")
    lc_events = [e for e in events if e["event_type"] == "template_lifecycle_changed"]
    assert len(lc_events) == 1
    assert lc_events[0]["actor"] == "carol"
    assert lc_events[0]["reason"] == "EOL"


def test_lifecycle_change_draft_to_approved(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/draft_tmpl/lifecycle",
        json={"lifecycle_status": "approved"},
    )
    assert resp.status_code == 200
    assert gov.get_lifecycle("draft_tmpl") == "approved"


def test_lifecycle_change_approved_to_review(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/approved_tmpl/lifecycle",
        json={"lifecycle_status": "review"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /v1/templates/{id}/lifecycle — error cases
# ---------------------------------------------------------------------------

def test_lifecycle_change_invalid_status_returns_422(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/approved_tmpl/lifecycle",
        json={"lifecycle_status": "invalid_state"},
    )
    assert resp.status_code == 422


def test_lifecycle_change_unknown_template_returns_404(client_with_gov):
    client, gov = client_with_gov
    resp = client.post(
        "/v1/templates/nonexistent/lifecycle",
        json={"lifecycle_status": "approved"},
    )
    assert resp.status_code == 404


def test_lifecycle_change_no_governance_store_returns_503(tmp_path, reg):
    app.state.template_registry = reg
    app.state.governance_store = None
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/v1/templates/approved_tmpl/lifecycle",
        json={"lifecycle_status": "deprecated"},
    )
    assert resp.status_code == 503
    app.state.template_registry = None


# ---------------------------------------------------------------------------
# GET /v1/templates/{id}/governance — effective state
# ---------------------------------------------------------------------------

def test_governance_endpoint_returns_manifest_lifecycle(client_with_gov):
    client, gov = client_with_gov
    resp = client.get("/v1/templates/approved_tmpl/governance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycle_status"] == "approved"
    # No explicit pin — effective default is semver-highest non-deprecated version
    assert data["default_version"] == "2.0.0"
    assert data["deprecated_versions"] == []


def test_governance_endpoint_reflects_lifecycle_override(client_with_gov):
    client, gov = client_with_gov
    gov.set_lifecycle("approved_tmpl", "deprecated")
    resp = client.get("/v1/templates/approved_tmpl/governance")
    assert resp.json()["lifecycle_status"] == "deprecated"


def test_governance_endpoint_shows_default_version(client_with_gov):
    client, gov = client_with_gov
    gov.set_default_version("approved_tmpl", "2.0.0")
    resp = client.get("/v1/templates/approved_tmpl/governance")
    assert resp.json()["default_version"] == "2.0.0"


def test_governance_endpoint_shows_deprecated_versions(client_with_gov):
    client, gov = client_with_gov
    gov.deprecate_version("approved_tmpl", "1.0.0", reason="old")
    resp = client.get("/v1/templates/approved_tmpl/governance")
    data = resp.json()
    assert "1.0.0" in data["deprecated_versions"]


def test_governance_endpoint_not_found(client_with_gov):
    client, gov = client_with_gov
    resp = client.get("/v1/templates/nonexistent/governance")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /v1/templates/{id}/governance/audit
# ---------------------------------------------------------------------------

def test_audit_endpoint_empty_initially(client_with_gov):
    client, gov = client_with_gov
    resp = client.get("/v1/templates/approved_tmpl/governance/audit")
    assert resp.status_code == 200
    assert resp.json() == []


def test_audit_endpoint_returns_events_after_actions(client_with_gov):
    client, gov = client_with_gov
    client.post("/v1/templates/approved_tmpl/versions/2.0.0/promote", json={})
    client.post(
        "/v1/templates/approved_tmpl/lifecycle",
        json={"lifecycle_status": "review"},
    )
    resp = client.get("/v1/templates/approved_tmpl/governance/audit")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 2
    event_types = {e["event_type"] for e in events}
    assert "template_version_promoted" in event_types
    assert "template_lifecycle_changed" in event_types


def test_audit_endpoint_newest_first(client_with_gov):
    client, gov = client_with_gov
    client.post("/v1/templates/approved_tmpl/versions/1.0.0/promote", json={})
    client.post("/v1/templates/approved_tmpl/versions/2.0.0/promote", json={})
    resp = client.get("/v1/templates/approved_tmpl/governance/audit")
    events = resp.json()
    # Most recent promotion (2.0.0) should appear first
    assert events[0]["template_version"] == "2.0.0"


def test_audit_endpoint_limit_param(client_with_gov):
    client, gov = client_with_gov
    for v in ["1.0.0", "2.0.0", "1.0.0", "2.0.0"]:
        client.post(f"/v1/templates/approved_tmpl/versions/{v}/promote", json={})
    resp = client.get("/v1/templates/approved_tmpl/governance/audit?limit=2")
    assert len(resp.json()) == 2


def test_audit_endpoint_not_found(client_with_gov):
    client, gov = client_with_gov
    resp = client.get("/v1/templates/nonexistent/governance/audit")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# resolve_template_for_run — lifecycle enforcement
# ---------------------------------------------------------------------------

def test_resolution_blocked_for_draft_with_governance(reg, gov):
    result = resolve_template_for_run(reg, "draft_tmpl", governance=gov)
    assert result is None


def test_resolution_blocked_for_deprecated_manifest(reg, gov):
    result = resolve_template_for_run(reg, "deprecated_tmpl", governance=gov)
    assert result is None


def test_resolution_blocked_when_lifecycle_overridden_to_deprecated(reg, gov):
    gov.set_lifecycle("approved_tmpl", "deprecated")
    result = resolve_template_for_run(reg, "approved_tmpl", governance=gov)
    assert result is None


def test_resolution_allowed_after_lifecycle_overridden_to_approved(reg, gov):
    gov.set_lifecycle("draft_tmpl", "approved")
    result = resolve_template_for_run(reg, "draft_tmpl", governance=gov)
    assert result is not None
    assert result.version == "0.1.0"


def test_resolution_blocked_for_deprecated_version_pinned(reg, gov):
    gov.deprecate_version("approved_tmpl", "1.0.0", reason="old")
    result = resolve_template_for_run(reg, "approved_tmpl", version="1.0.0", governance=gov)
    assert result is None


def test_resolution_allowed_for_non_deprecated_pinned_version(reg, gov):
    gov.deprecate_version("approved_tmpl", "1.0.0", reason="old")
    result = resolve_template_for_run(reg, "approved_tmpl", version="2.0.0", governance=gov)
    assert result is not None
    assert result.version == "2.0.0"


def test_resolution_uses_governance_default_over_semver(reg, gov):
    gov.set_default_version("approved_tmpl", "1.0.0")
    result = resolve_template_for_run(reg, "approved_tmpl", governance=gov)
    assert result is not None
    assert result.version == "1.0.0"


def test_resolution_falls_back_to_semver_when_pinned_deprecated(reg, gov):
    gov.set_default_version("approved_tmpl", "1.0.0")
    gov.deprecate_version("approved_tmpl", "1.0.0", reason="bad")
    result = resolve_template_for_run(reg, "approved_tmpl", governance=gov)
    assert result is not None
    assert result.version == "2.0.0"


# ---------------------------------------------------------------------------
# resolve_template_for_replay — lifecycle NOT enforced (replay safety)
# ---------------------------------------------------------------------------

def test_replay_resolves_despite_deprecated_template(reg, gov):
    """Deprecated templates must remain replayable."""
    result = resolve_template_for_replay(reg, "deprecated_tmpl", "1.0.0", governance=gov)
    assert result is not None
    assert result.version == "1.0.0"


def test_replay_resolves_despite_lifecycle_override_to_deprecated(reg, gov):
    gov.set_lifecycle("approved_tmpl", "deprecated")
    result = resolve_template_for_replay(reg, "approved_tmpl", "1.0.0", governance=gov)
    assert result is not None
    assert result.version == "1.0.0"


def test_replay_resolves_deprecated_version(reg, gov):
    """Deprecated versions must remain replayable."""
    gov.deprecate_version("approved_tmpl", "1.0.0", reason="old")
    result = resolve_template_for_replay(reg, "approved_tmpl", "1.0.0", governance=gov)
    assert result is not None
    assert result.version == "1.0.0"


def test_replay_returns_none_for_missing_version(reg, gov):
    result = resolve_template_for_replay(reg, "approved_tmpl", "9.9.9", governance=gov)
    assert result is None


# ---------------------------------------------------------------------------
# GET /v1/templates/{id} lifecycle reflects governance override
# ---------------------------------------------------------------------------

def test_template_detail_lifecycle_reflects_governance_override(client_with_gov):
    client, gov = client_with_gov
    gov.set_lifecycle("approved_tmpl", "deprecated")
    resp = client.get("/v1/templates/approved_tmpl")
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "deprecated"


def test_template_detail_lifecycle_uses_manifest_without_override(client_with_gov):
    client, gov = client_with_gov
    resp = client.get("/v1/templates/draft_tmpl")
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "draft"
