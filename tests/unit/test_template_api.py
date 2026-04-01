"""Tests for template registry API endpoints — Phase 8 Stage 1.

Covers:
- GET /v1/templates/{template_id}        → TemplateDetailResponse
- GET /v1/templates/{template_id}/versions → list[TemplateVersionResponse]
- GET /v1/templates (legacy)             → TemplatesResponse (backward compat)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.templates.models import Template, TemplateVersion
from pptgen.templates.registry import VersionedTemplateRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_version(template_id: str, version: str, **kw) -> TemplateVersion:
    return TemplateVersion(
        version_id=f"vid-{version}",
        template_id=template_id,
        version=version,
        template_revision_hash="ab12cd34ef56ab12",
        **kw,
    )


def _make_template(
    template_id: str,
    name: str = "Test Template",
    lifecycle_status: str = "approved",
    versions: list[str] | None = None,
    **kw,
) -> Template:
    vers = [_make_version(template_id, v) for v in (versions or ["1.0.0"])]
    return Template(
        template_id=template_id,
        template_key=template_id,
        name=name,
        lifecycle_status=lifecycle_status,
        versions=vers,
        **kw,
    )


@pytest.fixture
def client_with_registry():
    reg = VersionedTemplateRegistry([
        _make_template(
            "exec_brief",
            name="Executive Brief",
            lifecycle_status="approved",
            versions=["1.0.0", "2.0.0"],
            description="Exec deck",
            owner="Analytics",
        ),
        _make_template(
            "arch_overview",
            name="Architecture Overview",
            lifecycle_status="draft",
        ),
    ])
    app.state.template_registry = reg
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.state.template_registry = None


@pytest.fixture
def client_no_registry():
    app.state.template_registry = None
    client = TestClient(app, raise_server_exceptions=False)
    yield client


# ---------------------------------------------------------------------------
# GET /v1/templates/{template_id}
# ---------------------------------------------------------------------------

def test_get_template_ok(client_with_registry):
    client = client_with_registry
    resp = client.get("/v1/templates/exec_brief")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == "exec_brief"
    assert data["name"] == "Executive Brief"
    assert data["lifecycle_status"] == "approved"
    assert data["description"] == "Exec deck"
    assert data["owner"] == "Analytics"
    assert "1.0.0" in data["versions"]
    assert "2.0.0" in data["versions"]


def test_get_template_not_found(client_with_registry):
    client = client_with_registry
    resp = client.get("/v1/templates/nonexistent")
    assert resp.status_code == 404


def test_get_template_registry_unavailable(client_no_registry):
    client = client_no_registry
    resp = client.get("/v1/templates/exec_brief")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /v1/templates/{template_id}/versions
# ---------------------------------------------------------------------------

def test_list_versions_ok(client_with_registry):
    client = client_with_registry
    resp = client.get("/v1/templates/exec_brief/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    versions_found = {v["version"] for v in data}
    assert versions_found == {"1.0.0", "2.0.0"}


def test_list_versions_contains_hash(client_with_registry):
    client = client_with_registry
    resp = client.get("/v1/templates/exec_brief/versions")
    assert resp.status_code == 200
    for entry in resp.json():
        assert "template_revision_hash" in entry
        assert len(entry["template_revision_hash"]) == 16


def test_list_versions_not_found(client_with_registry):
    client = client_with_registry
    resp = client.get("/v1/templates/nonexistent/versions")
    assert resp.status_code == 404


def test_list_versions_registry_unavailable(client_no_registry):
    resp = client_no_registry.get("/v1/templates/exec_brief/versions")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Backward compatibility: GET /v1/templates
# ---------------------------------------------------------------------------

def test_legacy_templates_endpoint_returns_ids(client_with_registry):
    """The pre-existing GET /v1/templates endpoint still returns {request_id, templates:[...]}."""
    client = client_with_registry
    resp = client.get("/v1/templates")
    assert resp.status_code == 200
    data = resp.json()
    # Legacy schema requires request_id and templates list of strings
    assert "request_id" in data
    assert "templates" in data
    assert isinstance(data["templates"], list)
    # All items are strings (IDs), not objects
    for item in data["templates"]:
        assert isinstance(item, str)


def test_legacy_templates_endpoint_independent_of_registry(client_no_registry):
    """Legacy endpoint works even if template_registry is None."""
    resp = client_no_registry.get("/v1/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert "templates" in data


# ---------------------------------------------------------------------------
# Version ordering via GET /v1/templates/{id}/versions
# ---------------------------------------------------------------------------

def test_versions_returned_in_semver_order(client_with_registry):
    """Versions should come back sorted ascending by semver."""
    client = client_with_registry
    resp = client.get("/v1/templates/exec_brief/versions")
    assert resp.status_code == 200
    ver_strings = [v["version"] for v in resp.json()]
    assert ver_strings == sorted(ver_strings, key=lambda v: tuple(int(x) for x in v.split(".")))
