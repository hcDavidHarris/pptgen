"""Unit tests for Phase 10A Step 3 — resolve_artifact_version().

Covers:
- explicit version returns that version when present in governance index
- explicit version returns None when version is unknown
- explicit version returns None when artifact does not exist
- unversioned lookup returns default_version when declared
- unversioned lookup returns None when no default_version is declared
- unversioned lookup returns None when artifact does not exist
- lifecycle status is NOT enforced (draft/deprecated return normally)
- governance loaded on-demand (cold registry, no prior getter call)
- governance loaded via getter path (hot cache, same result)
- all five canonical artifact types work
- existing getters unchanged after adding resolve_artifact_version()
- idempotent: two calls return the same result
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pptgen.design_system import DesignSystemRegistry


DESIGN_SYSTEM_PATH = Path("design_system")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prim_yaml(
    primitive_id: str = "test_prim",
    version: str = "1.0.0",
    status: str = "approved",
    default_version: str | None = None,
) -> str:
    # Build without textwrap.dedent to avoid indentation conflicts when
    # family_block is interpolated — it would have different indentation than
    # the surrounding template and cause PyYAML parse errors.
    family_block = (
        f"family:\n  default_version: \"{default_version}\"\n"
        if default_version is not None
        else ""
    )
    return (
        f"schema_version: 1\n"
        f"primitive_id: {primitive_id}\n"
        f"version: \"{version}\"\n"
        f"layout_id: single_column\n"
        f"constraints:\n"
        f"  allow_extra_content: false\n"
        f"slots:\n"
        f"  title:\n"
        f"    required: true\n"
        f"    content_type: string\n"
        f"    maps_to: content\n"
        f"    description: \"Heading\"\n"
        f"governance:\n"
        f"  status: {status}\n"
        f"{family_block}"
    )


def _make_registry_with_prim(tmp_path: Path, **kwargs) -> DesignSystemRegistry:
    ds = tmp_path / "ds"
    (ds / "primitives").mkdir(parents=True)
    primitive_id = kwargs.get("primitive_id", "test_prim")
    (ds / "primitives" / f"{primitive_id}.yaml").write_text(
        _make_prim_yaml(**kwargs), encoding="utf-8"
    )
    return DesignSystemRegistry(ds)


# ---------------------------------------------------------------------------
# TestResolveArtifactVersionExplicit — Case 1: version is provided
# ---------------------------------------------------------------------------


class TestResolveArtifactVersionExplicit:
    def test_known_version_returned(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.2.3")
        result = reg.resolve_artifact_version("primitive", "test_prim", "1.2.3")
        assert result == "1.2.3"

    def test_unknown_version_returns_none(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0")
        result = reg.resolve_artifact_version("primitive", "test_prim", "9.9.9")
        assert result is None

    def test_nonexistent_artifact_returns_none(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("primitive", "ghost_prim", "1.0.0")
        assert result is None

    def test_unknown_artifact_type_returns_none(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("widget", "something", "1.0.0")
        assert result is None

    def test_returns_string_not_gov_object(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="2.0.0")
        result = reg.resolve_artifact_version("primitive", "test_prim", "2.0.0")
        assert isinstance(result, str)

    def test_exact_version_string_preserved(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0-beta")
        result = reg.resolve_artifact_version("primitive", "test_prim", "1.0.0-beta")
        assert result == "1.0.0-beta"


# ---------------------------------------------------------------------------
# TestResolveArtifactVersionDefault — Case 2: version is None
# ---------------------------------------------------------------------------


class TestResolveArtifactVersionDefault:
    def test_default_version_returned_when_declared(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="3.0.0", default_version="3.0.0")
        result = reg.resolve_artifact_version("primitive", "test_prim")
        assert result == "3.0.0"

    def test_no_default_returns_none(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0")  # no default_version
        result = reg.resolve_artifact_version("primitive", "test_prim")
        assert result is None

    def test_nonexistent_artifact_returns_none(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("primitive", "no_such_prim")
        assert result is None

    def test_unknown_artifact_type_returns_none(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("widget", "anything")
        assert result is None

    def test_real_primitive_without_default_returns_none(self):
        """Real design_system artifacts have no family.default_version declared."""
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("primitive", "bullet_slide")
        assert result is None

    def test_default_version_is_string(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.5.0", default_version="1.5.0")
        result = reg.resolve_artifact_version("primitive", "test_prim")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# TestResolveLifecycleNonEnforcement — no blocking for draft/deprecated
# ---------------------------------------------------------------------------


class TestResolveLifecycleNonEnforcement:
    """Phase 10A must NOT enforce lifecycle — all statuses resolve the same way."""

    def test_draft_artifact_explicit_version_returns_normally(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="0.1.0", status="draft")
        result = reg.resolve_artifact_version("primitive", "test_prim", "0.1.0")
        assert result == "0.1.0"

    def test_draft_artifact_default_version_returns_normally(self, tmp_path):
        reg = _make_registry_with_prim(
            tmp_path, version="0.1.0", status="draft", default_version="0.1.0"
        )
        result = reg.resolve_artifact_version("primitive", "test_prim")
        assert result == "0.1.0"

    def test_deprecated_artifact_explicit_version_returns_normally(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", status="deprecated")
        result = reg.resolve_artifact_version("primitive", "test_prim", "1.0.0")
        assert result == "1.0.0"

    def test_deprecated_artifact_default_version_returns_normally(self, tmp_path):
        reg = _make_registry_with_prim(
            tmp_path, version="1.0.0", status="deprecated", default_version="1.0.0"
        )
        result = reg.resolve_artifact_version("primitive", "test_prim")
        assert result == "1.0.0"


# ---------------------------------------------------------------------------
# TestResolveArtifactVersionLoadingPaths — cold vs hot cache
# ---------------------------------------------------------------------------


class TestResolveArtifactVersionLoadingPaths:
    def test_cold_cache_no_prior_getter(self, tmp_path):
        """resolve_artifact_version() loads governance itself when cache is empty."""
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", default_version="1.0.0")
        # No getter called first
        result = reg.resolve_artifact_version("primitive", "test_prim")
        assert result == "1.0.0"

    def test_hot_cache_after_getter(self, tmp_path):
        """Same result when getter has already populated the cache."""
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", default_version="1.0.0")
        reg.get_primitive("test_prim")  # warm cache
        result = reg.resolve_artifact_version("primitive", "test_prim")
        assert result == "1.0.0"

    def test_result_is_idempotent(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", default_version="1.0.0")
        r1 = reg.resolve_artifact_version("primitive", "test_prim")
        r2 = reg.resolve_artifact_version("primitive", "test_prim")
        assert r1 == r2


# ---------------------------------------------------------------------------
# TestResolveAllArtifactTypes — all five canonical types work
# ---------------------------------------------------------------------------


class TestResolveAllArtifactTypes:
    """Tests against the real design_system/ directory — single version per artifact."""

    def test_primitive_explicit_version(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("primitive", "bullet_slide", "1.0.0")
        assert result == "1.0.0"

    def test_layout_explicit_version(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("layout", "single_column", "1.0.0")
        assert result == "1.0.0"

    def test_theme_explicit_version(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("theme", "executive", "1.0.0")
        assert result == "1.0.0"

    def test_asset_explicit_version(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("asset", "icon.check", "1.0.0")
        assert result == "1.0.0"

    def test_token_set_explicit_version(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("token_set", "base", "1.0.0")
        assert result == "1.0.0"

    def test_wrong_version_returns_none_for_real_artifact(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        result = reg.resolve_artifact_version("primitive", "title_slide", "0.0.1")
        assert result is None

    def test_all_types_return_none_for_unknown_version(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        for artifact_type, artifact_id in [
            ("primitive", "comparison_slide"),
            ("layout", "two_column"),
            ("theme", "technical"),
            ("asset", "icon.warning"),
        ]:
            result = reg.resolve_artifact_version(artifact_type, artifact_id, "99.0.0")
            assert result is None, f"Expected None for {artifact_type}/{artifact_id}"


# ---------------------------------------------------------------------------
# TestExistingGettersUnchanged — regression guard
# ---------------------------------------------------------------------------


class TestExistingGettersUnchanged:
    def test_get_primitive_return_type_unchanged(self):
        from pptgen.design_system.primitive_models import SlidePrimitiveDefinition
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        p = reg.get_primitive("bullet_slide")
        assert isinstance(p, SlidePrimitiveDefinition)
        assert p.primitive_id == "bullet_slide"

    def test_get_layout_return_type_unchanged(self):
        from pptgen.design_system.layout_models import LayoutDefinition
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        lay = reg.get_layout("single_column")
        assert isinstance(lay, LayoutDefinition)

    def test_get_theme_return_type_unchanged(self):
        from pptgen.design_system.models import ThemePack
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        t = reg.get_theme("executive")
        assert isinstance(t, ThemePack)

    def test_get_asset_return_type_unchanged(self):
        from pptgen.design_system.asset_models import AssetDefinition
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        a = reg.get_asset("icon.check")
        assert isinstance(a, AssetDefinition)

    def test_resolve_does_not_affect_subsequent_getter(self):
        """resolve_artifact_version() must not corrupt the governance index."""
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        reg.resolve_artifact_version("primitive", "metrics_slide", "1.0.0")
        p = reg.get_primitive("metrics_slide")
        assert p.primitive_id == "metrics_slide"
