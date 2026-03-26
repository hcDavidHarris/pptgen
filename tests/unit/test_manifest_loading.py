"""Tests for template manifest loading — Phase 8 Stage 1."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pptgen.errors import RegistryError
from pptgen.templates.manifest_loader import (
    compute_template_revision_hash,
    load_template_manifest,
    validate_manifest_schema,
)
from pptgen.templates.models import Template, TemplateVersion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_manifest(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "templates.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


_MINIMAL_YAML = """\
    templates:
      tmpl_a:
        name: "Template A"
        lifecycle_status: approved
        versions:
          - version: "1.0.0"
            template_path: templates/tmpl_a/template.pptx
            input_contract_version: v1
            ai_mode: optional
"""

_MULTI_VERSION_YAML = """\
    templates:
      tmpl_b:
        name: "Template B"
        owner: "Team X"
        lifecycle_status: approved
        versions:
          - version: "1.0.0"
            template_path: templates/tmpl_b/v1/template.pptx
            ai_mode: optional
          - version: "2.0.0"
            template_path: templates/tmpl_b/v2/template.pptx
            ai_mode: required
"""


# ---------------------------------------------------------------------------
# validate_manifest_schema
# ---------------------------------------------------------------------------

def test_validate_requires_dict():
    with pytest.raises(RegistryError, match="must be a YAML mapping"):
        validate_manifest_schema([])


def test_validate_requires_templates_key():
    with pytest.raises(RegistryError, match="top-level 'templates' key"):
        validate_manifest_schema({})


def test_validate_templates_must_be_dict():
    with pytest.raises(RegistryError, match="mapping of template_id"):
        validate_manifest_schema({"templates": ["a", "b"]})


def test_validate_entry_must_have_versions():
    with pytest.raises(RegistryError, match="must have a 'versions' list"):
        validate_manifest_schema({"templates": {"tmpl_a": {"name": "A"}}})


def test_validate_versions_must_be_nonempty():
    with pytest.raises(RegistryError, match="at least one version"):
        validate_manifest_schema({"templates": {"tmpl_a": {"versions": []}}})


def test_validate_version_entry_must_have_version_field():
    with pytest.raises(RegistryError, match="must have a 'version' field"):
        validate_manifest_schema(
            {"templates": {"tmpl_a": {"versions": [{"template_path": "x.pptx"}]}}}
        )


def test_validate_passes_for_valid_data():
    validate_manifest_schema(
        {
            "templates": {
                "tmpl_a": {
                    "versions": [{"version": "1.0.0"}]
                }
            }
        }
    )  # no exception


# ---------------------------------------------------------------------------
# compute_template_revision_hash
# ---------------------------------------------------------------------------

def test_revision_hash_is_16_chars():
    h = compute_template_revision_hash("tmpl_a", "1.0.0", {})
    assert len(h) == 16
    assert h.isalnum()


def test_revision_hash_changes_with_template_id():
    h1 = compute_template_revision_hash("tmpl_a", "1.0.0", {})
    h2 = compute_template_revision_hash("tmpl_b", "1.0.0", {})
    assert h1 != h2


def test_revision_hash_changes_with_version():
    h1 = compute_template_revision_hash("tmpl_a", "1.0.0", {})
    h2 = compute_template_revision_hash("tmpl_a", "2.0.0", {})
    assert h1 != h2


def test_revision_hash_changes_with_template_path():
    h1 = compute_template_revision_hash("tmpl_a", "1.0.0", {"template_path": "a.pptx"})
    h2 = compute_template_revision_hash("tmpl_a", "1.0.0", {"template_path": "b.pptx"})
    assert h1 != h2


def test_revision_hash_is_deterministic():
    entry = {"template_path": "p.pptx", "input_contract_version": "v1", "ai_mode": "optional"}
    h1 = compute_template_revision_hash("tmpl_a", "1.0.0", entry)
    h2 = compute_template_revision_hash("tmpl_a", "1.0.0", entry)
    assert h1 == h2


# ---------------------------------------------------------------------------
# load_template_manifest — happy path
# ---------------------------------------------------------------------------

def test_load_minimal_manifest(tmp_path):
    p = _write_manifest(tmp_path, _MINIMAL_YAML)
    templates = load_template_manifest(p)
    assert len(templates) == 1
    tmpl = templates[0]
    assert tmpl.template_id == "tmpl_a"
    assert tmpl.name == "Template A"
    assert tmpl.lifecycle_status == "approved"
    assert len(tmpl.versions) == 1
    ver = tmpl.versions[0]
    assert ver.version == "1.0.0"
    assert ver.template_path == "templates/tmpl_a/template.pptx"
    assert ver.input_contract_version == "v1"
    assert ver.ai_mode == "optional"
    assert len(ver.template_revision_hash) == 16


def test_load_multi_version_manifest(tmp_path):
    p = _write_manifest(tmp_path, _MULTI_VERSION_YAML)
    templates = load_template_manifest(p)
    assert len(templates) == 1
    tmpl = templates[0]
    assert len(tmpl.versions) == 2
    versions_by_ver = {v.version: v for v in tmpl.versions}
    assert "1.0.0" in versions_by_ver
    assert "2.0.0" in versions_by_ver
    assert versions_by_ver["2.0.0"].ai_mode == "required"


def test_load_populates_version_id(tmp_path):
    p = _write_manifest(tmp_path, _MINIMAL_YAML)
    templates = load_template_manifest(p)
    ver = templates[0].versions[0]
    assert ver.version_id  # non-empty UUID string
    assert len(ver.version_id) == 36  # UUID format


def test_load_populates_owner_and_description(tmp_path):
    yaml = """\
        templates:
          tmpl_c:
            name: "Template C"
            owner: "Ops Team"
            description: "For ops reviews."
            lifecycle_status: draft
            versions:
              - version: "0.1.0"
    """
    p = _write_manifest(tmp_path, yaml)
    templates = load_template_manifest(p)
    assert templates[0].owner == "Ops Team"
    assert templates[0].description == "For ops reviews."
    assert templates[0].lifecycle_status == "draft"


def test_load_defaults_ai_mode_to_optional(tmp_path):
    yaml = """\
        templates:
          tmpl_d:
            name: "D"
            lifecycle_status: approved
            versions:
              - version: "1.0.0"
    """
    p = _write_manifest(tmp_path, yaml)
    templates = load_template_manifest(p)
    assert templates[0].versions[0].ai_mode == "optional"


# ---------------------------------------------------------------------------
# load_template_manifest — error paths
# ---------------------------------------------------------------------------

def test_load_raises_on_missing_file(tmp_path):
    with pytest.raises(RegistryError, match="Cannot read template manifest"):
        load_template_manifest(tmp_path / "nonexistent.yaml")


def test_load_raises_on_invalid_yaml(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(": : : invalid : yaml :", encoding="utf-8")
    with pytest.raises(RegistryError, match="YAML parse error"):
        load_template_manifest(p)


def test_load_raises_on_schema_violation(tmp_path):
    p = _write_manifest(tmp_path, "templates:\n  tmpl_a:\n    name: no versions\n")
    with pytest.raises(RegistryError):
        load_template_manifest(p)


# ---------------------------------------------------------------------------
# Round-trip: hash stability across calls
# ---------------------------------------------------------------------------

def test_revision_hash_stable_across_loads(tmp_path):
    """Same manifest loaded twice → same hashes."""
    p = _write_manifest(tmp_path, _MINIMAL_YAML)
    t1 = load_template_manifest(p)
    t2 = load_template_manifest(p)
    assert t1[0].versions[0].template_revision_hash == t2[0].versions[0].template_revision_hash
