"""Tests for VersionedTemplateRegistry — Phase 8 Stage 1."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pptgen.templates.models import Template, TemplateVersion
from pptgen.templates.registry import VersionedTemplateRegistry, _parse_semver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_version(template_id: str, version: str, **kw) -> TemplateVersion:
    from datetime import datetime, timezone
    return TemplateVersion(
        version_id=f"vid-{template_id}-{version}",
        template_id=template_id,
        version=version,
        template_revision_hash="abc123def456ab12",
        **kw,
    )


def _make_template(
    template_id: str,
    lifecycle_status: str = "approved",
    versions: list[str] | None = None,
) -> Template:
    from datetime import datetime, timezone
    vers = [_make_version(template_id, v) for v in (versions or ["1.0.0"])]
    return Template(
        template_id=template_id,
        template_key=template_id,
        name=template_id.replace("_", " ").title(),
        lifecycle_status=lifecycle_status,
        versions=vers,
    )


def _registry(*templates: Template) -> VersionedTemplateRegistry:
    return VersionedTemplateRegistry(list(templates))


# ---------------------------------------------------------------------------
# _parse_semver
# ---------------------------------------------------------------------------

def test_parse_semver_basic():
    assert _parse_semver("1.2.3") == (1, 2, 3)


def test_parse_semver_single_part():
    assert _parse_semver("2") == (2,)


def test_parse_semver_invalid_returns_zero():
    assert _parse_semver("not-a-version") == (0,)


def test_parse_semver_ordering():
    versions = ["2.0.0", "1.0.0", "1.10.0", "1.2.0"]
    sorted_v = sorted(versions, key=_parse_semver)
    assert sorted_v == ["1.0.0", "1.2.0", "1.10.0", "2.0.0"]


# ---------------------------------------------------------------------------
# VersionedTemplateRegistry basics
# ---------------------------------------------------------------------------

def test_list_templates_empty():
    reg = _registry()
    assert reg.list_templates() == []


def test_list_templates_returns_all():
    reg = _registry(_make_template("tmpl_a"), _make_template("tmpl_b"))
    ids = {t.template_id for t in reg.list_templates()}
    assert ids == {"tmpl_a", "tmpl_b"}


def test_get_template_found():
    reg = _registry(_make_template("tmpl_a"))
    t = reg.get_template("tmpl_a")
    assert t is not None
    assert t.template_id == "tmpl_a"


def test_get_template_not_found():
    reg = _registry(_make_template("tmpl_a"))
    assert reg.get_template("nonexistent") is None


def test_get_template_versions_sorted_ascending():
    tmpl = _make_template("tmpl_a", versions=["2.0.0", "1.0.0", "1.5.0"])
    reg = _registry(tmpl)
    versions = reg.get_template_versions("tmpl_a")
    assert [v.version for v in versions] == ["1.0.0", "1.5.0", "2.0.0"]


def test_get_template_versions_unknown_returns_empty():
    reg = _registry(_make_template("tmpl_a"))
    assert reg.get_template_versions("nonexistent") == []


def test_get_template_version_exact_match():
    tmpl = _make_template("tmpl_a", versions=["1.0.0", "2.0.0"])
    reg = _registry(tmpl)
    v = reg.get_template_version("tmpl_a", "1.0.0")
    assert v is not None
    assert v.version == "1.0.0"


def test_get_template_version_not_found():
    tmpl = _make_template("tmpl_a", versions=["1.0.0"])
    reg = _registry(tmpl)
    assert reg.get_template_version("tmpl_a", "9.9.9") is None


def test_get_approved_templates_filters_correctly():
    approved = _make_template("tmpl_a", lifecycle_status="approved")
    draft = _make_template("tmpl_b", lifecycle_status="draft")
    deprecated = _make_template("tmpl_c", lifecycle_status="deprecated")
    reg = _registry(approved, draft, deprecated)
    result = reg.get_approved_templates()
    assert len(result) == 1
    assert result[0].template_id == "tmpl_a"


def test_get_approved_templates_empty():
    reg = _registry(_make_template("tmpl_a", lifecycle_status="draft"))
    assert reg.get_approved_templates() == []


# ---------------------------------------------------------------------------
# from_manifest + default_manifest_path
# ---------------------------------------------------------------------------

def test_from_manifest_loads_real_yaml(tmp_path):
    yaml_content = textwrap.dedent("""\
        templates:
          test_tmpl:
            name: "Test Template"
            lifecycle_status: approved
            versions:
              - version: "1.0.0"
    """)
    p = tmp_path / "templates.yaml"
    p.write_text(yaml_content)
    reg = VersionedTemplateRegistry.from_manifest(p)
    assert reg.get_template("test_tmpl") is not None


def test_default_manifest_path_exists():
    path = VersionedTemplateRegistry.default_manifest_path()
    # The path should point to templates/registry/templates.yaml in the repo
    assert path.name == "templates.yaml"
    assert path.exists(), f"Default manifest not found at {path}"


def test_from_default_manifest_loads_production_templates():
    """Smoke test: the production manifest is valid and loads without error."""
    path = VersionedTemplateRegistry.default_manifest_path()
    reg = VersionedTemplateRegistry.from_manifest(path)
    templates = reg.list_templates()
    assert len(templates) >= 1
    for t in templates:
        assert t.template_id
        assert t.lifecycle_status in ("draft", "review", "approved", "deprecated")
        assert len(t.versions) >= 1
        for v in t.versions:
            assert v.version
            assert len(v.template_revision_hash) == 16
