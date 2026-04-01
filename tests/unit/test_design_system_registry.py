"""Tests for DesignSystemRegistry — Phase 9 Stage 1.

Covers:
- Loading base token set from YAML
- Loading brand packs
- Loading theme packs (with @version suffix support)
- list_themes() / list_brands()
- Schema validation errors
- Missing file errors
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from pptgen.design_system.exceptions import (
    DesignSystemSchemaError,
    UnknownBrandError,
    UnknownThemeError,
)
from pptgen.design_system.registry import DesignSystemRegistry


# ---------------------------------------------------------------------------
# Fixtures — build a minimal design_system/ tree in tmp_path
# ---------------------------------------------------------------------------

BASE_TOKENS_YAML = textwrap.dedent("""\
    schema_version: 1
    version: "1.0.0"
    tokens:
      color.primary: "#000000"
      color.secondary: "#333333"
      font.family.primary: "Calibri"
      font.size.title: 40
      spacing.md: 16
""")

BRAND_YAML = textwrap.dedent("""\
    schema_version: 1
    brand_id: acme
    version: "2.0.0"
    token_overrides:
      color.primary: "#0047AB"
      font.family.primary: "Inter"
""")

THEME_YAML = textwrap.dedent("""\
    schema_version: 1
    theme_id: executive
    version: "1.1.0"
    brand_id: acme
    token_overrides:
      font.size.title: 48
""")


def _make_registry(tmp_path: Path) -> DesignSystemRegistry:
    (tmp_path / "tokens").mkdir()
    (tmp_path / "brands").mkdir()
    (tmp_path / "themes").mkdir()
    (tmp_path / "tokens" / "base_tokens.yaml").write_text(BASE_TOKENS_YAML)
    (tmp_path / "brands" / "acme.yaml").write_text(BRAND_YAML)
    (tmp_path / "themes" / "executive.yaml").write_text(THEME_YAML)
    return DesignSystemRegistry(tmp_path)


# ---------------------------------------------------------------------------
# Base token set
# ---------------------------------------------------------------------------

class TestLoadBaseTokens:
    def test_version(self, tmp_path):
        reg = _make_registry(tmp_path)
        base = reg.load_base_tokens()
        assert base.version == "1.0.0"

    def test_schema_version(self, tmp_path):
        reg = _make_registry(tmp_path)
        base = reg.load_base_tokens()
        assert base.schema_version == 1

    def test_token_keys_present(self, tmp_path):
        reg = _make_registry(tmp_path)
        base = reg.load_base_tokens()
        assert "color.primary" in base.tokens
        assert "font.size.title" in base.tokens

    def test_string_token_value(self, tmp_path):
        reg = _make_registry(tmp_path)
        base = reg.load_base_tokens()
        assert base.tokens["color.primary"] == "#000000"

    def test_int_token_value(self, tmp_path):
        reg = _make_registry(tmp_path)
        base = reg.load_base_tokens()
        assert base.tokens["font.size.title"] == 40
        assert isinstance(base.tokens["font.size.title"], int)

    def test_missing_file_raises_schema_error(self, tmp_path):
        reg = DesignSystemRegistry(tmp_path / "nonexistent")
        with pytest.raises(DesignSystemSchemaError, match="not found"):
            reg.load_base_tokens()

    def test_missing_tokens_key_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            version: "1.0.0"
        """)
        (tmp_path / "tokens").mkdir(exist_ok=True)
        (tmp_path / "tokens" / "base_tokens.yaml").write_text(bad)
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(DesignSystemSchemaError, match="tokens"):
            reg.load_base_tokens()

    def test_invalid_yaml_raises(self, tmp_path):
        (tmp_path / "tokens").mkdir(exist_ok=True)
        (tmp_path / "tokens" / "base_tokens.yaml").write_text("{{bad yaml}}")
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(DesignSystemSchemaError, match="YAML"):
            reg.load_base_tokens()


# ---------------------------------------------------------------------------
# Brand pack
# ---------------------------------------------------------------------------

class TestGetBrand:
    def test_brand_id(self, tmp_path):
        reg = _make_registry(tmp_path)
        brand = reg.get_brand("acme")
        assert brand.brand_id == "acme"

    def test_brand_version(self, tmp_path):
        reg = _make_registry(tmp_path)
        brand = reg.get_brand("acme")
        assert brand.version == "2.0.0"

    def test_token_overrides_loaded(self, tmp_path):
        reg = _make_registry(tmp_path)
        brand = reg.get_brand("acme")
        assert brand.token_overrides["color.primary"] == "#0047AB"
        assert brand.token_overrides["font.family.primary"] == "Inter"

    def test_unknown_brand_raises(self, tmp_path):
        reg = _make_registry(tmp_path)
        with pytest.raises(UnknownBrandError, match="no_such_brand"):
            reg.get_brand("no_such_brand")

    def test_unknown_brand_error_lists_available(self, tmp_path):
        reg = _make_registry(tmp_path)
        with pytest.raises(UnknownBrandError, match="acme"):
            reg.get_brand("unknown")

    def test_brand_empty_overrides_allowed(self, tmp_path):
        minimal = textwrap.dedent("""\
            schema_version: 1
            brand_id: minimal
            version: "1.0.0"
            token_overrides:
        """)
        (tmp_path / "brands").mkdir(exist_ok=True)
        (tmp_path / "brands" / "minimal.yaml").write_text(minimal)
        reg = DesignSystemRegistry(tmp_path)
        brand = reg.get_brand("minimal")
        assert brand.token_overrides == {}

    def test_missing_required_key_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            brand_id: bad
            token_overrides:
        """)
        (tmp_path / "brands").mkdir(exist_ok=True)
        (tmp_path / "brands" / "bad.yaml").write_text(bad)
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(DesignSystemSchemaError, match="version"):
            reg.get_brand("bad")


# ---------------------------------------------------------------------------
# Theme pack
# ---------------------------------------------------------------------------

class TestGetTheme:
    def test_theme_id(self, tmp_path):
        reg = _make_registry(tmp_path)
        theme = reg.get_theme("executive")
        assert theme.theme_id == "executive"

    def test_theme_version(self, tmp_path):
        reg = _make_registry(tmp_path)
        theme = reg.get_theme("executive")
        assert theme.version == "1.1.0"

    def test_brand_id(self, tmp_path):
        reg = _make_registry(tmp_path)
        theme = reg.get_theme("executive")
        assert theme.brand_id == "acme"

    def test_token_overrides_loaded(self, tmp_path):
        reg = _make_registry(tmp_path)
        theme = reg.get_theme("executive")
        assert theme.token_overrides["font.size.title"] == 48

    def test_at_version_suffix_stripped(self, tmp_path):
        reg = _make_registry(tmp_path)
        theme = reg.get_theme("executive@v2")
        assert theme.theme_id == "executive"

    def test_unknown_theme_raises(self, tmp_path):
        reg = _make_registry(tmp_path)
        with pytest.raises(UnknownThemeError, match="no_such_theme"):
            reg.get_theme("no_such_theme")

    def test_unknown_theme_error_lists_available(self, tmp_path):
        reg = _make_registry(tmp_path)
        with pytest.raises(UnknownThemeError, match="executive"):
            reg.get_theme("unknown")

    def test_theme_empty_overrides_allowed(self, tmp_path):
        no_overrides = textwrap.dedent("""\
            schema_version: 1
            theme_id: plain
            version: "1.0.0"
            brand_id: acme
        """)
        (tmp_path / "themes").mkdir(exist_ok=True)
        (tmp_path / "themes" / "plain.yaml").write_text(no_overrides)
        reg = DesignSystemRegistry(tmp_path)
        theme = reg.get_theme("plain")
        assert theme.token_overrides == {}


# ---------------------------------------------------------------------------
# Discovery: list_themes / list_brands
# ---------------------------------------------------------------------------

class TestDiscovery:
    def test_list_themes_returns_registered(self, tmp_path):
        reg = _make_registry(tmp_path)
        assert "executive" in reg.list_themes()

    def test_list_brands_returns_registered(self, tmp_path):
        reg = _make_registry(tmp_path)
        assert "acme" in reg.list_brands()

    def test_list_themes_empty_when_dir_missing(self, tmp_path):
        reg = DesignSystemRegistry(tmp_path)
        assert reg.list_themes() == []

    def test_list_brands_empty_when_dir_missing(self, tmp_path):
        reg = DesignSystemRegistry(tmp_path)
        assert reg.list_brands() == []

    def test_list_themes_sorted(self, tmp_path):
        reg = _make_registry(tmp_path)
        # Add a second theme
        (tmp_path / "themes" / "aaa.yaml").write_text(textwrap.dedent("""\
            schema_version: 1
            theme_id: aaa
            version: "1.0.0"
            brand_id: acme
        """))
        themes = reg.list_themes()
        assert themes == sorted(themes)

    def test_multiple_brands_listed(self, tmp_path):
        reg = _make_registry(tmp_path)
        (tmp_path / "brands" / "otherbrand.yaml").write_text(textwrap.dedent("""\
            schema_version: 1
            brand_id: otherbrand
            version: "1.0.0"
            token_overrides:
        """))
        assert "acme" in reg.list_brands()
        assert "otherbrand" in reg.list_brands()


# ---------------------------------------------------------------------------
# Real design_system/ directory (smoke test)
# ---------------------------------------------------------------------------

_DESIGN_SYSTEM_ROOT = Path(__file__).parent.parent.parent / "design_system"


@pytest.mark.skipif(
    not _DESIGN_SYSTEM_ROOT.exists(),
    reason="design_system/ directory not present",
)
class TestRealDesignSystem:
    def test_base_tokens_load(self):
        reg = DesignSystemRegistry(_DESIGN_SYSTEM_ROOT)
        base = reg.load_base_tokens()
        assert "color.primary" in base.tokens
        assert "font.size.title" in base.tokens

    def test_healthcatalyst_brand_loads(self):
        reg = DesignSystemRegistry(_DESIGN_SYSTEM_ROOT)
        brand = reg.get_brand("healthcatalyst")
        assert brand.brand_id == "healthcatalyst"

    def test_executive_theme_loads(self):
        reg = DesignSystemRegistry(_DESIGN_SYSTEM_ROOT)
        theme = reg.get_theme("executive")
        assert theme.theme_id == "executive"
        assert theme.brand_id == "healthcatalyst"

    def test_technical_theme_loads(self):
        reg = DesignSystemRegistry(_DESIGN_SYSTEM_ROOT)
        theme = reg.get_theme("technical")
        assert theme.theme_id == "technical"

    def test_list_themes_includes_executive_and_technical(self):
        reg = DesignSystemRegistry(_DESIGN_SYSTEM_ROOT)
        themes = reg.list_themes()
        assert "executive" in themes
        assert "technical" in themes
