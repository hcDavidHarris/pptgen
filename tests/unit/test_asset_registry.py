"""Tests for asset artifact loading in DesignSystemRegistry — Phase 9 Stage 4.

Covers:
- Loading a valid asset definition
- asset_id, version, schema_version, type, source fields
- metadata loading (present and absent)
- list_assets() discovery
- Unknown asset → UnknownAssetError with available list
- Malformed YAML → InvalidAssetDefinitionError
- Missing required key → InvalidAssetDefinitionError
- Invalid type → InvalidAssetTypeError
- Non-mapping metadata → InvalidAssetDefinitionError
- Real design_system/ smoke tests
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pptgen.design_system.asset_models import AssetDefinition
from pptgen.design_system.exceptions import (
    InvalidAssetDefinitionError,
    InvalidAssetTypeError,
    UnknownAssetError,
)
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
    metadata:
      description: "Checkmark icon"
      alt_text: "Check"
""")

LOGO_YAML = textwrap.dedent("""\
    schema_version: 1
    asset_id: logo.company
    version: 2.0.0
    type: logo
    source: "assets/logos/company.svg"
""")

IMAGE_YAML = textwrap.dedent("""\
    schema_version: 1
    asset_id: image.hero
    version: 1.0.0
    type: image
    source: "assets/images/hero.png"
    metadata:
      width: 1920
      height: 1080
""")


def _make_registry(tmp_path: Path, assets: dict[str, str]) -> DesignSystemRegistry:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True)
    for name, content in assets.items():
        (assets_dir / f"{name}.yaml").write_text(content, encoding="utf-8")
    return DesignSystemRegistry(tmp_path)


# ---------------------------------------------------------------------------
# TestGetAsset — basic loading
# ---------------------------------------------------------------------------


class TestGetAsset:
    def test_loads_asset_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        asset = reg.get_asset("icon.check")
        assert asset.asset_id == "icon.check"

    def test_loads_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        asset = reg.get_asset("icon.check")
        assert asset.version == "1.0.0"

    def test_loads_schema_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        asset = reg.get_asset("icon.check")
        assert asset.schema_version == 1

    def test_loads_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        asset = reg.get_asset("icon.check")
        assert asset.type == "icon"

    def test_loads_source(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        asset = reg.get_asset("icon.check")
        assert asset.source == "assets/icons/check.svg"

    def test_loads_metadata(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        asset = reg.get_asset("icon.check")
        assert asset.metadata["alt_text"] == "Check"

    def test_metadata_defaults_to_empty_dict_when_absent(self, tmp_path):
        reg = _make_registry(tmp_path, {"logo.company": LOGO_YAML})
        asset = reg.get_asset("logo.company")
        assert asset.metadata == {}

    def test_logo_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"logo.company": LOGO_YAML})
        asset = reg.get_asset("logo.company")
        assert asset.type == "logo"

    def test_image_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"image.hero": IMAGE_YAML})
        asset = reg.get_asset("image.hero")
        assert asset.type == "image"

    def test_numeric_metadata_preserved(self, tmp_path):
        reg = _make_registry(tmp_path, {"image.hero": IMAGE_YAML})
        asset = reg.get_asset("image.hero")
        assert asset.metadata["width"] == 1920

    def test_returns_asset_definition_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        asset = reg.get_asset("icon.check")
        assert isinstance(asset, AssetDefinition)

    def test_dotted_id_lookup_works(self, tmp_path):
        reg = _make_registry(tmp_path, {"logo.company": LOGO_YAML})
        asset = reg.get_asset("logo.company")
        assert asset.asset_id == "logo.company"


# ---------------------------------------------------------------------------
# TestGetAssetErrors
# ---------------------------------------------------------------------------


class TestGetAssetErrors:
    def test_unknown_asset_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        with pytest.raises(UnknownAssetError):
            reg.get_asset("icon.nonexistent")

    def test_unknown_asset_lists_available(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        with pytest.raises(UnknownAssetError, match="icon.check"):
            reg.get_asset("icon.nonexistent")

    def test_unknown_asset_empty_dir(self, tmp_path):
        (tmp_path / "assets").mkdir()
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(UnknownAssetError, match="none"):
            reg.get_asset("icon.check")

    def test_missing_required_key_asset_id(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            version: 1.0.0
            type: icon
            source: "check.svg"
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidAssetDefinitionError, match="asset_id"):
            reg.get_asset("bad")

    def test_missing_required_key_source(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            asset_id: bad
            version: 1.0.0
            type: icon
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidAssetDefinitionError, match="source"):
            reg.get_asset("bad")

    def test_missing_required_key_type(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            asset_id: bad
            version: 1.0.0
            source: "bad.svg"
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidAssetDefinitionError, match="type"):
            reg.get_asset("bad")

    def test_invalid_type_raises_asset_type_error(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            asset_id: bad
            version: 1.0.0
            type: chart
            source: "bad.svg"
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidAssetTypeError, match="chart"):
            reg.get_asset("bad")

    def test_invalid_type_error_lists_valid_types(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            asset_id: bad
            version: 1.0.0
            type: animation
            source: "bad.gif"
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidAssetTypeError, match="icon"):
            reg.get_asset("bad")

    def test_metadata_not_mapping_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            asset_id: bad
            version: 1.0.0
            type: icon
            source: "bad.svg"
            metadata: "should be a mapping"
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidAssetDefinitionError):
            reg.get_asset("bad")

    def test_malformed_yaml_raises(self, tmp_path):
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir(parents=True)
        (assets_dir / "broken.check.yaml").write_text(": invalid: {\n", encoding="utf-8")
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(InvalidAssetDefinitionError):
            reg.get_asset("broken.check")


# ---------------------------------------------------------------------------
# TestListAssets
# ---------------------------------------------------------------------------


class TestListAssets:
    def test_returns_sorted_list(self, tmp_path):
        reg = _make_registry(tmp_path, {
            "logo.company": LOGO_YAML,
            "icon.check": ICON_CHECK_YAML,
        })
        assert reg.list_assets() == ["icon.check", "logo.company"]

    def test_empty_when_dir_missing(self, tmp_path):
        reg = DesignSystemRegistry(tmp_path)
        assert reg.list_assets() == []

    def test_empty_dir_returns_empty(self, tmp_path):
        (tmp_path / "assets").mkdir()
        reg = DesignSystemRegistry(tmp_path)
        assert reg.list_assets() == []

    def test_stem_includes_dots(self, tmp_path):
        reg = _make_registry(tmp_path, {"icon.check": ICON_CHECK_YAML})
        assert reg.list_assets() == ["icon.check"]


# ---------------------------------------------------------------------------
# TestRealAssetArtifacts
# ---------------------------------------------------------------------------


class TestRealAssetArtifacts:
    @pytest.fixture
    def real_registry(self):
        root = Path(__file__).parent.parent.parent / "design_system"
        return DesignSystemRegistry(root)

    def test_list_assets_non_empty(self, real_registry):
        assets = real_registry.list_assets()
        assert len(assets) >= 3

    def test_icon_check_loads(self, real_registry):
        asset = real_registry.get_asset("icon.check")
        assert asset.asset_id == "icon.check"
        assert asset.type == "icon"
        assert asset.source

    def test_icon_warning_loads(self, real_registry):
        asset = real_registry.get_asset("icon.warning")
        assert asset.type == "icon"

    def test_logo_company_loads(self, real_registry):
        asset = real_registry.get_asset("logo.company")
        assert asset.type == "logo"
