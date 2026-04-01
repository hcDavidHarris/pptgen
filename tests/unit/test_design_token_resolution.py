"""Tests for TokenResolver — Phase 9 Stage 1.

Covers:
- Precedence model: base → brand → theme
- Token reference substitution in deck definitions
- Validation of brand/theme overrides against the base token set
- ResolvedStyleMap fields and to_dict()
"""
from __future__ import annotations

import pytest

from pptgen.design_system.exceptions import InvalidTokenOverrideError, UnknownTokenError
from pptgen.design_system.models import BaseTokenSet, BrandPack, ThemePack
from pptgen.design_system.token_resolver import TokenResolver


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE = BaseTokenSet(
    version="1.0.0",
    schema_version=1,
    tokens={
        "color.primary": "#000000",
        "color.secondary": "#333333",
        "color.background": "#FFFFFF",
        "font.family.primary": "Calibri",
        "font.size.title": 40,
        "font.size.body": 18,
        "spacing.md": 16,
        "spacing.xl": 32,
    },
)

BRAND = BrandPack(
    brand_id="acme",
    version="1.0.0",
    schema_version=1,
    token_overrides={
        "color.primary": "#0047AB",
        "color.secondary": "#5BA6FF",
        "font.family.primary": "Inter",
    },
)

THEME = ThemePack(
    theme_id="executive",
    version="1.0.0",
    brand_id="acme",
    schema_version=1,
    token_overrides={
        "font.size.title": 48,
        "spacing.xl": 64,
    },
)


# ---------------------------------------------------------------------------
# Precedence model
# ---------------------------------------------------------------------------

class TestTokenPrecedence:
    def test_base_values_used_when_no_overrides(self):
        no_brand = BrandPack("acme", "1.0.0", 1, {})
        no_theme = ThemePack("plain", "1.0.0", "acme", 1, {})
        resolver = TokenResolver()
        style_map = resolver.resolve(BASE, no_brand, no_theme)
        assert style_map.tokens["color.primary"] == "#000000"
        assert style_map.tokens["font.size.title"] == 40

    def test_brand_overrides_base(self):
        no_theme = ThemePack("plain", "1.0.0", "acme", 1, {})
        resolver = TokenResolver()
        style_map = resolver.resolve(BASE, BRAND, no_theme)
        assert style_map.tokens["color.primary"] == "#0047AB"
        assert style_map.tokens["font.family.primary"] == "Inter"
        # Non-overridden base token is preserved
        assert style_map.tokens["color.background"] == "#FFFFFF"

    def test_theme_overrides_brand_and_base(self):
        resolver = TokenResolver()
        style_map = resolver.resolve(BASE, BRAND, THEME)
        # Theme overrides
        assert style_map.tokens["font.size.title"] == 48
        assert style_map.tokens["spacing.xl"] == 64
        # Brand overrides still present
        assert style_map.tokens["color.primary"] == "#0047AB"
        # Base value preserved where neither brand nor theme overrides
        assert style_map.tokens["color.background"] == "#FFFFFF"

    def test_theme_does_not_affect_un_overridden_brand_values(self):
        resolver = TokenResolver()
        style_map = resolver.resolve(BASE, BRAND, THEME)
        # Brand set font.family.primary; theme did not touch it
        assert style_map.tokens["font.family.primary"] == "Inter"

    def test_all_base_keys_present_in_resolved_map(self):
        resolver = TokenResolver()
        style_map = resolver.resolve(BASE, BRAND, THEME)
        assert set(style_map.tokens) == set(BASE.tokens)

    def test_theme_overrides_wins_over_same_key_in_brand(self):
        brand_with_title = BrandPack("x", "1.0.0", 1, {"font.size.title": 36})
        theme_with_title = ThemePack("y", "1.0.0", "x", 1, {"font.size.title": 52})
        resolver = TokenResolver()
        style_map = resolver.resolve(BASE, brand_with_title, theme_with_title)
        assert style_map.tokens["font.size.title"] == 52


# ---------------------------------------------------------------------------
# ResolvedStyleMap metadata
# ---------------------------------------------------------------------------

class TestResolvedStyleMapMetadata:
    def setup_method(self):
        self.resolver = TokenResolver()
        self.style_map = self.resolver.resolve(BASE, BRAND, THEME)

    def test_theme_id(self):
        assert self.style_map.theme_id == "executive"

    def test_theme_version(self):
        assert self.style_map.theme_version == "1.0.0"

    def test_brand_id(self):
        assert self.style_map.brand_id == "acme"

    def test_brand_version(self):
        assert self.style_map.brand_version == "1.0.0"

    def test_token_set_version(self):
        assert self.style_map.token_set_version == "1.0.0"

    def test_resolved_at_is_iso_timestamp(self):
        from datetime import datetime
        # Should parse without error
        datetime.fromisoformat(self.style_map.resolved_at)

    def test_get_existing_token(self):
        assert self.style_map.get("color.primary") == "#0047AB"

    def test_get_missing_token_returns_default(self):
        assert self.style_map.get("no.such.token") is None
        assert self.style_map.get("no.such.token", "fallback") == "fallback"

    def test_to_dict_contains_required_keys(self):
        d = self.style_map.to_dict()
        for key in ("theme_id", "theme_version", "brand_id", "brand_version",
                    "token_set_version", "resolved_at", "tokens"):
            assert key in d

    def test_to_dict_tokens_are_serialisable(self):
        import json
        d = self.style_map.to_dict()
        json.dumps(d)  # should not raise


# ---------------------------------------------------------------------------
# Token reference substitution
# ---------------------------------------------------------------------------

class TestTokenReferenceSubstitution:
    def setup_method(self):
        self.resolver = TokenResolver()
        self.style_map = self.resolver.resolve(BASE, BRAND, THEME)

    def test_string_token_ref_replaced(self):
        deck = {"slides": [{"title_color": "token.color.primary"}]}
        result = self.resolver.resolve_references(deck, self.style_map)
        assert result["slides"][0]["title_color"] == "#0047AB"

    def test_numeric_token_ref_replaced(self):
        deck = {"font_size": "token.font.size.title"}
        result = self.resolver.resolve_references(deck, self.style_map)
        assert result["font_size"] == 48

    def test_non_token_string_unchanged(self):
        deck = {"title": "Quarterly Report"}
        result = self.resolver.resolve_references(deck, self.style_map)
        assert result["title"] == "Quarterly Report"

    def test_nested_dict_substituted(self):
        deck = {
            "meta": {"color": "token.color.secondary"},
            "slides": [{"body_size": "token.font.size.body"}],
        }
        result = self.resolver.resolve_references(deck, self.style_map)
        assert result["meta"]["color"] == "#5BA6FF"
        assert result["slides"][0]["body_size"] == 18

    def test_list_values_substituted(self):
        deck = {"colors": ["token.color.primary", "token.color.background"]}
        result = self.resolver.resolve_references(deck, self.style_map)
        assert result["colors"] == ["#0047AB", "#FFFFFF"]

    def test_none_value_unchanged(self):
        deck = {"optional": None}
        result = self.resolver.resolve_references(deck, self.style_map)
        assert result["optional"] is None

    def test_integer_value_unchanged(self):
        deck = {"count": 42}
        result = self.resolver.resolve_references(deck, self.style_map)
        assert result["count"] == 42

    def test_unknown_token_reference_raises(self):
        deck = {"color": "token.no.such.token"}
        with pytest.raises(UnknownTokenError, match="no.such.token"):
            self.resolver.resolve_references(deck, self.style_map)

    def test_no_token_refs_deck_unchanged(self):
        deck = {"title": "Hello", "slides": [{"text": "Body copy", "size": 24}]}
        result = self.resolver.resolve_references(deck, self.style_map)
        assert result == deck


# ---------------------------------------------------------------------------
# Override validation
# ---------------------------------------------------------------------------

class TestOverrideValidation:
    def test_brand_unknown_token_raises(self):
        bad_brand = BrandPack("x", "1.0.0", 1, {"no.such.token": "#FF0000"})
        with pytest.raises(InvalidTokenOverrideError, match="no.such.token"):
            TokenResolver().resolve(BASE, bad_brand, ThemePack("t", "1.0.0", "x", 1, {}))

    def test_theme_unknown_token_raises(self):
        bad_theme = ThemePack("x", "1.0.0", "acme", 1, {"no.such.token": 99})
        with pytest.raises(InvalidTokenOverrideError, match="no.such.token"):
            TokenResolver().resolve(BASE, BRAND, bad_theme)

    def test_multiple_unknown_tokens_all_reported(self):
        bad_brand = BrandPack("x", "1.0.0", 1, {"alpha": 1, "beta": 2})
        with pytest.raises(InvalidTokenOverrideError) as exc_info:
            TokenResolver().resolve(BASE, bad_brand, ThemePack("t", "1.0.0", "x", 1, {}))
        msg = str(exc_info.value)
        assert "alpha" in msg
        assert "beta" in msg

    def test_valid_overrides_do_not_raise(self):
        brand = BrandPack("x", "1.0.0", 1, {"color.primary": "#123456"})
        theme = ThemePack("y", "1.0.0", "x", 1, {"font.size.title": 44})
        # Should not raise
        TokenResolver().resolve(BASE, brand, theme)

    def test_empty_overrides_do_not_raise(self):
        brand = BrandPack("x", "1.0.0", 1, {})
        theme = ThemePack("y", "1.0.0", "x", 1, {})
        TokenResolver().resolve(BASE, brand, theme)
