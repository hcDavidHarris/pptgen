"""Unit tests for Phase 10A governance registry integration.

Covers:
- artifact without governance block → lifecycle defaults to APPROVED, audit fields None
- artifact with governance block → all fields parsed correctly
- datetime field as string (quoted YAML) → parsed to datetime
- datetime field as native YAML timestamp → returned as datetime
- lifecycle status DRAFT and DEPRECATED are parsed
- invalid lifecycle value → DesignSystemSchemaError at load time
- family block with default_version → loaded correctly
- missing family block → default_version is None
- get_artifact_governance() returns correct version
- get_artifact_governance() returns None for unknown version
- get_artifact_family() returns GovernedArtifactFamily
- get_artifact_family() returns None for unknown artifact
- list_artifact_versions() returns list of one for current single-file design
- list_artifact_versions() returns empty list for unknown artifact
- on-demand loading (governance method called before any getter)
- existing getters return unchanged objects after governance wiring
- all five artifact types can load governance metadata
- governance is additive — existing test artifacts load without governance blocks
- _parse_gov_datetime handles None, datetime, string, "Z"-suffixed string
- _parse_lifecycle defaults to APPROVED when raw is None
"""
from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from pptgen.design_system import (
    DesignSystemRegistry,
    GovernedArtifactFamily,
    GovernedArtifactVersion,
    LifecycleStatus,
)
from pptgen.design_system.exceptions import DesignSystemSchemaError
from pptgen.design_system.registry import _parse_gov_datetime, _parse_governance_block, _parse_lifecycle


DESIGN_SYSTEM_PATH = Path("design_system")


# ---------------------------------------------------------------------------
# Helpers — in-memory YAML fixtures
# ---------------------------------------------------------------------------

def _make_primitive_yaml(governance: str = "", family: str = "") -> str:
    """Build a minimal valid primitive YAML with optional governance/family blocks."""
    return textwrap.dedent(f"""\
        schema_version: 1
        primitive_id: test_prim
        version: "2.0.0"
        layout_id: single_column
        constraints:
          allow_extra_content: false
        slots:
          title:
            required: true
            content_type: string
            maps_to: content
            description: "Heading"
        {governance}
        {family}
    """)


def _load_yaml_str(text: str) -> dict:
    return yaml.safe_load(text)


# ---------------------------------------------------------------------------
# TestParseGovDatetime — unit tests for the datetime helper
# ---------------------------------------------------------------------------


class TestParseGovDatetime:
    def test_none_returns_none(self):
        assert _parse_gov_datetime(None) is None

    def test_native_datetime_returned_unchanged(self):
        dt = datetime(2026, 3, 28, 12, 0, 0)
        assert _parse_gov_datetime(dt) is dt

    def test_iso_string_parsed(self):
        result = _parse_gov_datetime("2026-03-28T12:00:00")
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 3

    def test_z_suffix_normalized(self):
        result = _parse_gov_datetime("2026-03-28T12:00:00Z")
        assert isinstance(result, datetime)

    def test_invalid_string_returns_none(self):
        assert _parse_gov_datetime("not-a-date") is None

    def test_non_string_non_datetime_returns_none(self):
        assert _parse_gov_datetime(12345) is None


# ---------------------------------------------------------------------------
# TestParseLifecycle — unit tests for lifecycle parsing helper
# ---------------------------------------------------------------------------


class TestParseLifecycle:
    def test_none_defaults_to_approved(self, tmp_path):
        path = tmp_path / "x.yaml"
        assert _parse_lifecycle(None, path) == LifecycleStatus.APPROVED

    def test_approved_string_parsed(self, tmp_path):
        assert _parse_lifecycle("approved", tmp_path / "x.yaml") == LifecycleStatus.APPROVED

    def test_draft_string_parsed(self, tmp_path):
        assert _parse_lifecycle("draft", tmp_path / "x.yaml") == LifecycleStatus.DRAFT

    def test_deprecated_string_parsed(self, tmp_path):
        assert _parse_lifecycle("deprecated", tmp_path / "x.yaml") == LifecycleStatus.DEPRECATED

    def test_case_insensitive(self, tmp_path):
        assert _parse_lifecycle("APPROVED", tmp_path / "x.yaml") == LifecycleStatus.APPROVED

    def test_invalid_value_raises(self, tmp_path):
        with pytest.raises(DesignSystemSchemaError, match="Invalid governance status"):
            _parse_lifecycle("published", tmp_path / "x.yaml")

    def test_error_message_contains_valid_values(self, tmp_path):
        with pytest.raises(DesignSystemSchemaError, match="approved"):
            _parse_lifecycle("bad", tmp_path / "x.yaml")


# ---------------------------------------------------------------------------
# TestParseGovernanceBlock — unit tests for the compound block parser
# ---------------------------------------------------------------------------


class TestParseGovernanceBlock:
    def test_no_governance_block_defaults_approved(self, tmp_path):
        data = {"version": "1.0.0"}
        gov, _ = _parse_governance_block(data, "primitive", "x", "1.0.0", tmp_path / "x.yaml")
        assert gov.lifecycle_status == LifecycleStatus.APPROVED

    def test_governance_block_parsed_correctly(self, tmp_path):
        data = _load_yaml_str(textwrap.dedent("""\
            version: "1.1"
            governance:
              status: approved
              created_by: alice
              promoted_at: 2026-03-28T12:00:00Z
        """))
        gov, _ = _parse_governance_block(data, "primitive", "x", "1.1", tmp_path / "x.yaml")
        assert gov.lifecycle_status == LifecycleStatus.APPROVED
        assert gov.created_by == "alice"
        assert isinstance(gov.promoted_at, datetime)

    def test_draft_status_parsed(self, tmp_path):
        data = {"version": "1.0.0", "governance": {"status": "draft"}}
        gov, _ = _parse_governance_block(data, "layout", "y", "1.0.0", tmp_path / "y.yaml")
        assert gov.lifecycle_status == LifecycleStatus.DRAFT

    def test_deprecated_status_with_reason(self, tmp_path):
        data = {"version": "1.0.0", "governance": {
            "status": "deprecated",
            "deprecation_reason": "replaced by v2",
        }}
        gov, _ = _parse_governance_block(data, "asset", "z", "1.0.0", tmp_path / "z.yaml")
        assert gov.lifecycle_status == LifecycleStatus.DEPRECATED
        assert gov.deprecation_reason == "replaced by v2"

    def test_invalid_status_raises(self, tmp_path):
        data = {"version": "1.0.0", "governance": {"status": "published"}}
        with pytest.raises(DesignSystemSchemaError):
            _parse_governance_block(data, "primitive", "x", "1.0.0", tmp_path / "x.yaml")

    def test_no_family_block_yields_none_default(self, tmp_path):
        data = {"version": "1.0.0"}
        _, family = _parse_governance_block(data, "primitive", "x", "1.0.0", tmp_path / "x.yaml")
        assert family.default_version is None

    def test_family_default_version_loaded(self, tmp_path):
        data = {"version": "1.0.0", "family": {"default_version": "1.1"}}
        _, family = _parse_governance_block(data, "primitive", "x", "1.0.0", tmp_path / "x.yaml")
        assert family.default_version == "1.1"

    def test_returned_gov_carries_artifact_metadata(self, tmp_path):
        data = {"version": "3.0.0"}
        gov, family = _parse_governance_block(data, "theme", "executive", "3.0.0", tmp_path / "t.yaml")
        assert gov.artifact_id == "executive"
        assert gov.artifact_type == "theme"
        assert gov.version == "3.0.0"
        assert family.artifact_id == "executive"
        assert family.artifact_type == "theme"

    def test_all_audit_fields_none_when_absent(self, tmp_path):
        data = {"version": "1.0.0", "governance": {"status": "approved"}}
        gov, _ = _parse_governance_block(data, "primitive", "x", "1.0.0", tmp_path / "x.yaml")
        assert gov.created_at is None
        assert gov.created_by is None
        assert gov.promoted_at is None
        assert gov.promoted_by is None
        assert gov.deprecated_at is None
        assert gov.deprecated_by is None
        assert gov.deprecation_reason is None


# ---------------------------------------------------------------------------
# TestRegistryGovernanceIntegration — registry methods against real files
# ---------------------------------------------------------------------------


class TestRegistryGovernanceIntegration:
    """Tests against the actual design_system/ directory — no mocking."""

    @pytest.fixture
    def reg(self):
        return DesignSystemRegistry(DESIGN_SYSTEM_PATH)

    # ------------------------------------------------------------------ #
    # Existing getters remain unchanged                                    #
    # ------------------------------------------------------------------ #

    def test_get_primitive_unchanged(self, reg):
        p = reg.get_primitive("bullet_slide")
        assert p.primitive_id == "bullet_slide"
        assert p.version == "1.0.0"

    def test_get_layout_unchanged(self, reg):
        lay = reg.get_layout("single_column")
        assert lay.layout_id == "single_column"

    def test_get_theme_unchanged(self, reg):
        t = reg.get_theme("executive")
        assert t.theme_id == "executive"

    def test_get_asset_unchanged(self, reg):
        a = reg.get_asset("icon.check")
        assert a.asset_id == "icon.check"

    # ------------------------------------------------------------------ #
    # Governance populated via getter path                                 #
    # ------------------------------------------------------------------ #

    def test_governance_populated_after_get_primitive(self, reg):
        p = reg.get_primitive("bullet_slide")
        gov = reg.get_artifact_governance("primitive", "bullet_slide", p.version)
        assert gov is not None
        assert gov.artifact_id == "bullet_slide"
        assert gov.artifact_type == "primitive"

    def test_governance_defaults_to_approved_for_existing_primitive(self, reg):
        p = reg.get_primitive("title_slide")
        gov = reg.get_artifact_governance("primitive", "title_slide", p.version)
        assert gov.lifecycle_status == LifecycleStatus.APPROVED

    def test_governance_populated_after_get_layout(self, reg):
        lay = reg.get_layout("two_column")
        gov = reg.get_artifact_governance("layout", "two_column", lay.version)
        assert gov is not None
        assert gov.lifecycle_status == LifecycleStatus.APPROVED

    def test_governance_populated_after_get_theme(self, reg):
        t = reg.get_theme("executive")
        gov = reg.get_artifact_governance("theme", "executive", t.version)
        assert gov is not None

    def test_governance_populated_after_get_asset(self, reg):
        a = reg.get_asset("icon.check")
        gov = reg.get_artifact_governance("asset", "icon.check", a.version)
        assert gov is not None
        assert gov.artifact_type == "asset"

    # ------------------------------------------------------------------ #
    # get_artifact_governance — unknown cases                              #
    # ------------------------------------------------------------------ #

    def test_get_artifact_governance_unknown_version_returns_none(self, reg):
        reg.get_primitive("bullet_slide")
        gov = reg.get_artifact_governance("primitive", "bullet_slide", "99.0.0")
        assert gov is None

    def test_get_artifact_governance_unknown_artifact_returns_none(self, reg):
        gov = reg.get_artifact_governance("primitive", "nonexistent_slide", "1.0.0")
        assert gov is None

    # ------------------------------------------------------------------ #
    # get_artifact_family                                                  #
    # ------------------------------------------------------------------ #

    def test_get_artifact_family_returns_object(self, reg):
        reg.get_primitive("bullet_slide")
        fam = reg.get_artifact_family("primitive", "bullet_slide")
        assert isinstance(fam, GovernedArtifactFamily)
        assert fam.artifact_id == "bullet_slide"
        assert fam.artifact_type == "primitive"

    def test_get_artifact_family_no_family_block_default_version_none(self, reg):
        reg.get_primitive("comparison_slide")
        fam = reg.get_artifact_family("primitive", "comparison_slide")
        assert fam.default_version is None

    def test_get_artifact_family_unknown_artifact_returns_none(self, reg):
        fam = reg.get_artifact_family("primitive", "no_such_primitive")
        assert fam is None

    # ------------------------------------------------------------------ #
    # list_artifact_versions                                               #
    # ------------------------------------------------------------------ #

    def test_list_artifact_versions_single_version(self, reg):
        versions = reg.list_artifact_versions("primitive", "bullet_slide")
        assert len(versions) == 1
        assert isinstance(versions[0], GovernedArtifactVersion)
        assert versions[0].artifact_id == "bullet_slide"

    def test_list_artifact_versions_version_string_correct(self, reg):
        versions = reg.list_artifact_versions("primitive", "bullet_slide")
        assert versions[0].version == "1.0.0"

    def test_list_artifact_versions_unknown_returns_empty(self, reg):
        versions = reg.list_artifact_versions("primitive", "no_such_prim")
        assert versions == []

    def test_list_artifact_versions_layout(self, reg):
        versions = reg.list_artifact_versions("layout", "single_column")
        assert len(versions) == 1
        assert versions[0].artifact_type == "layout"

    # ------------------------------------------------------------------ #
    # On-demand loading (governance method before any getter)              #
    # ------------------------------------------------------------------ #

    def test_on_demand_load_without_prior_getter(self):
        """Governance method loads YAML itself when cache is cold."""
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        # No getter called first
        gov = reg.get_artifact_governance("primitive", "title_slide", "1.0.0")
        assert gov is not None
        assert gov.artifact_id == "title_slide"

    def test_on_demand_family_without_prior_getter(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        fam = reg.get_artifact_family("layout", "metric_dashboard")
        assert fam is not None
        assert fam.artifact_type == "layout"

    def test_on_demand_list_versions_without_prior_getter(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        versions = reg.list_artifact_versions("asset", "icon.warning")
        assert len(versions) == 1
        assert versions[0].artifact_id == "icon.warning"

    # ------------------------------------------------------------------ #
    # All five artifact types can be governed                              #
    # ------------------------------------------------------------------ #

    def test_token_set_governance(self, reg):
        reg.load_base_tokens()
        gov = reg.get_artifact_governance("token_set", "base", "1.0.0")
        assert gov is not None
        assert gov.artifact_type == "token_set"
        assert gov.lifecycle_status == LifecycleStatus.APPROVED

    def test_theme_governance(self, reg):
        gov = reg.get_artifact_governance("theme", "executive", "1.0.0")
        assert gov is not None

    def test_layout_governance(self, reg):
        gov = reg.get_artifact_governance("layout", "grid_2x2", "1.0.0")
        assert gov is not None

    def test_primitive_governance(self, reg):
        gov = reg.get_artifact_governance("primitive", "metrics_slide", "1.0.0")
        assert gov is not None

    def test_asset_governance(self, reg):
        gov = reg.get_artifact_governance("asset", "logo.company", "1.0.0")
        assert gov is not None

    # ------------------------------------------------------------------ #
    # Governance with explicit blocks (in-memory YAML via tmp_path)        #
    # ------------------------------------------------------------------ #

    def test_governance_block_parsed_in_full_registry(self, tmp_path):
        """Full registry load with governance block in a primitive YAML."""
        ds_root = tmp_path / "design_system"
        prim_dir = ds_root / "primitives"
        prim_dir.mkdir(parents=True)

        prim_yaml = textwrap.dedent("""\
            schema_version: 1
            primitive_id: governed_prim
            version: "2.0.0"
            layout_id: single_column
            constraints:
              allow_extra_content: false
            slots:
              title:
                required: true
                content_type: string
                maps_to: content
                description: "Heading"
            governance:
              status: approved
              created_by: alice
              promoted_at: "2026-03-28T12:00:00Z"
        """)
        (prim_dir / "governed_prim.yaml").write_text(prim_yaml, encoding="utf-8")

        reg = DesignSystemRegistry(ds_root)
        reg.get_primitive("governed_prim")  # trigger load

        gov = reg.get_artifact_governance("primitive", "governed_prim", "2.0.0")
        assert gov is not None
        assert gov.lifecycle_status == LifecycleStatus.APPROVED
        assert gov.created_by == "alice"
        assert isinstance(gov.promoted_at, datetime)

    def test_family_default_version_parsed_in_full_registry(self, tmp_path):
        ds_root = tmp_path / "design_system"
        prim_dir = ds_root / "primitives"
        prim_dir.mkdir(parents=True)

        prim_yaml = textwrap.dedent("""\
            schema_version: 1
            primitive_id: family_prim
            version: "1.1.0"
            layout_id: single_column
            constraints:
              allow_extra_content: false
            slots:
              title:
                required: true
                content_type: string
                maps_to: content
                description: "Heading"
            family:
              default_version: "1.1.0"
        """)
        (prim_dir / "family_prim.yaml").write_text(prim_yaml, encoding="utf-8")

        reg = DesignSystemRegistry(ds_root)
        reg.get_primitive("family_prim")

        fam = reg.get_artifact_family("primitive", "family_prim")
        assert fam.default_version == "1.1.0"

    def test_invalid_governance_status_raises_at_load_time(self, tmp_path):
        ds_root = tmp_path / "design_system"
        prim_dir = ds_root / "primitives"
        prim_dir.mkdir(parents=True)

        bad_yaml = textwrap.dedent("""\
            schema_version: 1
            primitive_id: bad_prim
            version: "1.0.0"
            layout_id: single_column
            constraints:
              allow_extra_content: false
            slots:
              title:
                required: true
                content_type: string
                maps_to: content
                description: "Heading"
            governance:
              status: published
        """)
        (prim_dir / "bad_prim.yaml").write_text(bad_yaml, encoding="utf-8")

        reg = DesignSystemRegistry(ds_root)
        with pytest.raises(DesignSystemSchemaError, match="Invalid governance status"):
            reg.get_primitive("bad_prim")

    def test_deprecated_artifact_loads_with_reason(self, tmp_path):
        ds_root = tmp_path / "design_system"
        (ds_root / "primitives").mkdir(parents=True)

        dep_yaml = textwrap.dedent("""\
            schema_version: 1
            primitive_id: old_prim
            version: "1.0.0"
            layout_id: single_column
            constraints:
              allow_extra_content: false
            slots:
              title:
                required: true
                content_type: string
                maps_to: content
                description: "Heading"
            governance:
              status: deprecated
              deprecation_reason: "superseded by new_prim"
        """)
        (ds_root / "primitives" / "old_prim.yaml").write_text(dep_yaml, encoding="utf-8")

        reg = DesignSystemRegistry(ds_root)
        reg.get_primitive("old_prim")

        gov = reg.get_artifact_governance("primitive", "old_prim", "1.0.0")
        assert gov.lifecycle_status == LifecycleStatus.DEPRECATED
        assert "superseded" in gov.deprecation_reason

    # ------------------------------------------------------------------ #
    # Idempotency — loading same artifact twice uses cache                 #
    # ------------------------------------------------------------------ #

    def test_governance_load_idempotent(self, reg):
        reg.get_primitive("bullet_slide")
        reg.get_primitive("bullet_slide")  # second call
        versions = reg.list_artifact_versions("primitive", "bullet_slide")
        assert len(versions) == 1  # not duplicated
