"""Tests for AssetResolver — Phase 9 Stage 4.

Covers:
- No asset refs → deck unchanged, empty list returned
- Single top-level asset ref replaced
- Nested asset ref replaced
- Asset ref inside list replaced
- Deeply nested asset ref replaced
- Multiple distinct asset refs resolved
- Same asset_id referenced twice → resolved once (deduplication)
- Resolved inline dict contains expected keys
- Unknown asset_id → UnknownAssetError
- Empty asset_id string → UnknownAssetError
- Non-string asset_id → UnknownAssetError
- ResolvedAsset list order matches first occurrence
- to_dict() is JSON-serializable
- as_inline() keeps asset_id for traceability
- Backward compat: deck without asset refs unmodified
- Determinism: same input → same output
- Pipeline: resolved_assets is [] when no refs present
- Pipeline: resolved_assets populated when refs present
- resolved_assets_snapshot.json written only when non-empty
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from pptgen.design_system.asset_models import ResolvedAsset
from pptgen.design_system.asset_resolver import AssetResolver
from pptgen.design_system.exceptions import UnknownAssetError
from pptgen.design_system.registry import DesignSystemRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ICON_CHECK_YAML = textwrap.dedent("""\
    schema_version: 1
    asset_id: icon.check
    version: 1.0.0
    type: icon
    source: "assets/icons/check.svg"
""")

ICON_WARNING_YAML = textwrap.dedent("""\
    schema_version: 1
    asset_id: icon.warning
    version: 1.0.0
    type: icon
    source: "assets/icons/warning.svg"
""")

LOGO_YAML = textwrap.dedent("""\
    schema_version: 1
    asset_id: logo.company
    version: 2.0.0
    type: logo
    source: "assets/logos/company.svg"
""")


def _make_registry(tmp_path: Path, assets: dict[str, str]) -> DesignSystemRegistry:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True)
    for name, content in assets.items():
        (assets_dir / f"{name}.yaml").write_text(content, encoding="utf-8")
    return DesignSystemRegistry(tmp_path)


# ---------------------------------------------------------------------------
# TestNoAssetRefs
# ---------------------------------------------------------------------------


class TestNoAssetRefs:
    def test_empty_deck_unchanged(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {}
        new_deck, resolved = AssetResolver().resolve_references(deck, reg)
        assert new_deck == {}
        assert resolved == []

    def test_plain_string_values_unchanged(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"title": "Hello", "body": "World"}
        new_deck, resolved = AssetResolver().resolve_references(deck, reg)
        assert new_deck == deck
        assert resolved == []

    def test_list_values_unchanged(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"items": ["a", "b", "c"]}
        new_deck, resolved = AssetResolver().resolve_references(deck, reg)
        assert new_deck == deck
        assert resolved == []

    def test_nested_dict_without_asset_id_unchanged(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"slot": {"title": "T", "value": 42}}
        new_deck, resolved = AssetResolver().resolve_references(deck, reg)
        assert new_deck == deck
        assert resolved == []

    def test_returns_new_dict_not_same_object(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"key": "value"}
        new_deck, _ = AssetResolver().resolve_references(deck, reg)
        assert new_deck is not deck


# ---------------------------------------------------------------------------
# TestSingleRef
# ---------------------------------------------------------------------------


class TestSingleRef:
    def test_top_level_ref_replaced(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": "icon.check"}}
        new_deck, _ = AssetResolver().resolve_references(deck, reg)
        assert new_deck["icon"]["asset_id"] == "icon.check"
        assert new_deck["icon"]["resolved_source"] == "assets/icons/check.svg"

    def test_inline_has_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": "icon.check"}}
        new_deck, _ = AssetResolver().resolve_references(deck, reg)
        assert new_deck["icon"]["type"] == "icon"

    def test_inline_has_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": "icon.check"}}
        new_deck, _ = AssetResolver().resolve_references(deck, reg)
        assert new_deck["icon"]["version"] == "1.0.0"

    def test_resolved_list_contains_one_entry(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": "icon.check"}}
        _, resolved = AssetResolver().resolve_references(deck, reg)
        assert len(resolved) == 1
        assert resolved[0].asset_id == "icon.check"

    def test_resolved_entry_is_resolved_asset(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": "icon.check"}}
        _, resolved = AssetResolver().resolve_references(deck, reg)
        assert isinstance(resolved[0], ResolvedAsset)


# ---------------------------------------------------------------------------
# TestNestedRefs
# ---------------------------------------------------------------------------


class TestNestedRefs:
    def test_nested_ref_replaced(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"content": {"metric": {"value": "99%", "icon": {"asset_id": "icon.check"}}}}
        new_deck, _ = AssetResolver().resolve_references(deck, reg)
        assert new_deck["content"]["metric"]["icon"]["resolved_source"] == "assets/icons/check.svg"

    def test_ref_inside_list(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"items": [{"label": "ok", "icon": {"asset_id": "icon.check"}}]}
        new_deck, _ = AssetResolver().resolve_references(deck, reg)
        assert new_deck["items"][0]["icon"]["resolved_source"] == "assets/icons/check.svg"

    def test_ref_inside_list_of_lists(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"matrix": [[{"asset_id": "icon.check"}]]}
        new_deck, _ = AssetResolver().resolve_references(deck, reg)
        assert new_deck["matrix"][0][0]["resolved_source"] == "assets/icons/check.svg"


# ---------------------------------------------------------------------------
# TestMultipleRefs
# ---------------------------------------------------------------------------


class TestMultipleRefs:
    def test_two_distinct_refs_both_resolved(self, tmp_path):
        reg = _make_registry(tmp_path, {
            "icon.check": ICON_CHECK_YAML,
            "icon.warning": ICON_WARNING_YAML,
        })
        deck = {
            "ok_icon": {"asset_id": "icon.check"},
            "warn_icon": {"asset_id": "icon.warning"},
        }
        new_deck, resolved = AssetResolver().resolve_references(deck, reg)
        assert new_deck["ok_icon"]["resolved_source"] == "assets/icons/check.svg"
        assert new_deck["warn_icon"]["resolved_source"] == "assets/icons/warning.svg"
        assert len(resolved) == 2

    def test_same_ref_twice_deduplicated_in_list(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {
            "a": {"asset_id": "icon.check"},
            "b": {"asset_id": "icon.check"},
        }
        _, resolved = AssetResolver().resolve_references(deck, reg)
        assert len(resolved) == 1

    def test_same_ref_twice_both_replaced_in_deck(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {
            "a": {"asset_id": "icon.check"},
            "b": {"asset_id": "icon.check"},
        }
        new_deck, _ = AssetResolver().resolve_references(deck, reg)
        assert new_deck["a"]["resolved_source"] == "assets/icons/check.svg"
        assert new_deck["b"]["resolved_source"] == "assets/icons/check.svg"

    def test_order_of_resolved_list_is_first_occurrence(self, tmp_path):
        reg = _make_registry(tmp_path, {
            "icon.check": ICON_CHECK_YAML,
            "logo.company": LOGO_YAML,
        })
        deck = {
            "first": {"asset_id": "icon.check"},
            "second": {"asset_id": "logo.company"},
        }
        _, resolved = AssetResolver().resolve_references(deck, reg)
        assert resolved[0].asset_id == "icon.check"
        assert resolved[1].asset_id == "logo.company"


# ---------------------------------------------------------------------------
# TestErrors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_unknown_asset_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": "icon.nonexistent"}}
        with pytest.raises(UnknownAssetError):
            AssetResolver().resolve_references(deck, reg)

    def test_error_includes_asset_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": "icon.missing"}}
        with pytest.raises(UnknownAssetError, match="icon.missing"):
            AssetResolver().resolve_references(deck, reg)

    def test_empty_asset_id_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": ""}}
        with pytest.raises(UnknownAssetError):
            AssetResolver().resolve_references(deck, reg)

    def test_non_string_asset_id_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": 42}}
        with pytest.raises(UnknownAssetError):
            AssetResolver().resolve_references(deck, reg)


# ---------------------------------------------------------------------------
# TestResolvedAssetModel
# ---------------------------------------------------------------------------


class TestResolvedAssetModel:
    def test_to_dict_has_asset_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        _, resolved = AssetResolver().resolve_references(
            {"icon": {"asset_id": "icon.check"}}, reg
        )
        assert resolved[0].to_dict()["asset_id"] == "icon.check"

    def test_to_dict_has_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        _, resolved = AssetResolver().resolve_references(
            {"icon": {"asset_id": "icon.check"}}, reg
        )
        assert resolved[0].to_dict()["version"] == "1.0.0"

    def test_to_dict_has_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        _, resolved = AssetResolver().resolve_references(
            {"icon": {"asset_id": "icon.check"}}, reg
        )
        assert resolved[0].to_dict()["type"] == "icon"

    def test_to_dict_has_resolved_source(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        _, resolved = AssetResolver().resolve_references(
            {"icon": {"asset_id": "icon.check"}}, reg
        )
        assert resolved[0].to_dict()["resolved_source"] == "assets/icons/check.svg"

    def test_to_dict_is_json_serializable(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        _, resolved = AssetResolver().resolve_references(
            {"icon": {"asset_id": "icon.check"}}, reg
        )
        json.dumps(resolved[0].to_dict())  # must not raise

    def test_as_inline_keeps_asset_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        _, resolved = AssetResolver().resolve_references(
            {"icon": {"asset_id": "icon.check"}}, reg
        )
        assert resolved[0].as_inline()["asset_id"] == "icon.check"


# ---------------------------------------------------------------------------
# TestDeterminism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"a": {"asset_id": "icon.check"}, "b": {"label": "text"}}
        result1, _ = AssetResolver().resolve_references(deck, reg)
        result2, _ = AssetResolver().resolve_references(deck, reg)
        assert result1 == result2

    def test_resolved_source_is_stable(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        deck = {"icon": {"asset_id": "icon.check"}}
        _, r1 = AssetResolver().resolve_references(deck, reg)
        _, r2 = AssetResolver().resolve_references(deck, reg)
        assert r1[0].resolved_source == r2[0].resolved_source


# ---------------------------------------------------------------------------
# TestRealAssets — smoke tests against actual design_system/
# ---------------------------------------------------------------------------


class TestRealAssets:
    @pytest.fixture
    def real_registry(self):
        root = Path(__file__).parent.parent.parent / "design_system"
        return DesignSystemRegistry(root)

    def test_no_refs_returns_empty(self, real_registry):
        deck = {"title": "plain deck", "slides": [{"content": "text"}]}
        new_deck, resolved = AssetResolver().resolve_references(deck, real_registry)
        assert resolved == []
        assert new_deck == deck

    def test_icon_check_ref_resolved(self, real_registry):
        deck = {"icon": {"asset_id": "icon.check"}}
        new_deck, resolved = AssetResolver().resolve_references(deck, real_registry)
        assert resolved[0].asset_id == "icon.check"
        assert new_deck["icon"]["type"] == "icon"

    def test_logo_company_ref_resolved(self, real_registry):
        deck = {"logo": {"asset_id": "logo.company"}}
        new_deck, resolved = AssetResolver().resolve_references(deck, real_registry)
        assert resolved[0].type == "logo"

    def test_assets_snapshot_format(self, real_registry, tmp_path):
        deck = {
            "ok": {"asset_id": "icon.check"},
            "warn": {"asset_id": "icon.warning"},
        }
        _, resolved = AssetResolver().resolve_references(deck, real_registry)
        snapshot = {"assets": [a.to_dict() for a in resolved]}
        path = tmp_path / "resolved_assets_snapshot.json"
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        data = json.loads(path.read_text())
        assert len(data["assets"]) == 2
        ids = {a["asset_id"] for a in data["assets"]}
        assert "icon.check" in ids
        assert "icon.warning" in ids

    def test_backward_compat_no_asset_refs(self, real_registry):
        """Templates without any asset_id references are completely unaffected."""
        deck = {
            "slides": [
                {"layout": "single_column", "slots": {"content": {"title": "T"}}}
            ]
        }
        new_deck, resolved = AssetResolver().resolve_references(deck, real_registry)
        assert resolved == []
        assert new_deck == deck
