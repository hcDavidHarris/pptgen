"""Unit tests for the TemplateRegistry.

Tests cover loading, lookup, and error conditions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.errors import RegistryError
from pptgen.registry.registry import TemplateEntry, TemplateRegistry


class TestTemplateRegistryLoading:
    def test_loads_from_valid_file(self, fixtures_dir: Path):
        registry = TemplateRegistry.from_file(fixtures_dir / "test_registry.yaml")
        assert len(registry.all()) == 2

    def test_file_not_found_raises_registry_error(self, tmp_path: Path):
        with pytest.raises(RegistryError, match="Cannot read registry file"):
            TemplateRegistry.from_file(tmp_path / "does_not_exist.yaml")

    def test_malformed_yaml_raises_registry_error(self, tmp_path: Path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("templates: [invalid: yaml: :::]\n")
        with pytest.raises(RegistryError):
            TemplateRegistry.from_file(bad_file)

    def test_missing_templates_key_raises_registry_error(self, tmp_path: Path):
        bad_file = tmp_path / "no_key.yaml"
        bad_file.write_text("not_templates:\n  - id: foo\n")
        with pytest.raises(RegistryError, match="top-level 'templates'"):
            TemplateRegistry.from_file(bad_file)

    def test_empty_templates_list_is_valid(self, tmp_path: Path):
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("templates: []\n")
        registry = TemplateRegistry.from_file(empty_file)
        assert registry.all() == []


class TestTemplateRegistryLookup:
    def test_get_existing_template(self, test_registry: TemplateRegistry):
        entry = test_registry.get("ops_review_v1")
        assert entry is not None
        assert entry.template_id == "ops_review_v1"
        assert entry.status == "approved"

    def test_get_missing_template_returns_none(self, test_registry: TemplateRegistry):
        assert test_registry.get("nonexistent") is None

    def test_exists_true_for_registered(self, test_registry: TemplateRegistry):
        assert test_registry.exists("ops_review_v1") is True

    def test_exists_false_for_unregistered(self, test_registry: TemplateRegistry):
        assert test_registry.exists("not_there") is False

    def test_all_returns_all_entries(self, test_registry: TemplateRegistry):
        entries = test_registry.all()
        ids = [e.template_id for e in entries]
        assert "ops_review_v1" in ids
        assert "draft_template_v1" in ids

    def test_draft_template_is_accessible(self, test_registry: TemplateRegistry):
        entry = test_registry.get("draft_template_v1")
        assert entry is not None
        assert entry.status == "draft"

    def test_entry_fields_correct(self, test_registry: TemplateRegistry):
        entry = test_registry.get("ops_review_v1")
        assert entry.version == "1.0"
        assert entry.owner == "Test Team"
        assert "title" in entry.supported_slide_types
        assert "metric_summary" in entry.supported_slide_types

    def test_max_metrics_defaults_to_4(self, test_registry: TemplateRegistry):
        entry = test_registry.get("ops_review_v1")
        assert entry.max_metrics == 4


class TestTemplateEntry:
    def test_extra_fields_ignored(self):
        """Registry entries use extra='ignore' to handle future registry fields."""
        entry = TemplateEntry.model_validate(
            {
                "template_id": "t",
                "version": "1.0",
                "owner": "Team",
                "status": "approved",
                "path": "templates/t/template.pptx",
                "supported_slide_types": ["title"],
                "future_field": "this should be ignored",
            }
        )
        assert entry.template_id == "t"
