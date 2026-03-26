"""Tests for layout artifact loading in DesignSystemRegistry — Phase 9 Stage 2.

Covers:
- Loading a valid layout definition
- Region required/optional flag
- Constraints loading (allow_extra_slots)
- Missing layout → UnknownLayoutError with available list
- Malformed layout YAML → InvalidLayoutDefinitionError
- Missing required key → InvalidLayoutDefinitionError
- Non-mapping regions block → InvalidLayoutDefinitionError
- Non-mapping region entry → InvalidLayoutDefinitionError
- list_layouts() discovery
- Real design_system/ smoke tests
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pptgen.design_system.exceptions import InvalidLayoutDefinitionError, UnknownLayoutError
from pptgen.design_system.layout_models import LayoutDefinition, RegionDefinition
from pptgen.design_system.registry import DesignSystemRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SINGLE_COL_YAML = textwrap.dedent("""\
    schema_version: 1
    layout_id: single_column
    version: 1.0.0
    constraints:
      allow_extra_slots: false
    regions:
      content:
        required: true
        label: "Main Content"
        position:
          x: 5
          y: 15
          width: 90
          height: 80
""")

TWO_COL_YAML = textwrap.dedent("""\
    schema_version: 1
    layout_id: two_column
    version: 1.0.0
    constraints:
      allow_extra_slots: false
    regions:
      left:
        required: true
        label: "Left Column"
      right:
        required: false
        label: "Right Column"
""")

METRIC_YAML = textwrap.dedent("""\
    schema_version: 1
    layout_id: metric_dashboard
    version: 2.0.0
    constraints:
      allow_extra_slots: true
    regions:
      headline:
        required: true
        label: "Headline"
      detail:
        required: false
        label: "Detail"
""")


def _make_registry(tmp_path: Path, layouts: dict[str, str]) -> DesignSystemRegistry:
    layouts_dir = tmp_path / "layouts"
    layouts_dir.mkdir(parents=True)
    for name, content in layouts.items():
        (layouts_dir / f"{name}.yaml").write_text(content, encoding="utf-8")
    return DesignSystemRegistry(tmp_path)


# ---------------------------------------------------------------------------
# TestGetLayout — basic loading
# ---------------------------------------------------------------------------


class TestGetLayout:
    def test_loads_layout_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert layout.layout_id == "single_column"

    def test_loads_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert layout.version == "1.0.0"

    def test_loads_schema_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert layout.schema_version == 1

    def test_loads_regions(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert "content" in layout.regions

    def test_region_required_flag_true(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert layout.regions["content"].required is True

    def test_region_required_flag_false(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        layout = reg.get_layout("two_column")
        assert layout.regions["right"].required is False

    def test_region_label(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert layout.regions["content"].label == "Main Content"

    def test_region_position(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert layout.regions["content"].position["x"] == 5

    def test_constraints_allow_extra_slots_false(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert layout.constraints.allow_extra_slots is False

    def test_constraints_allow_extra_slots_true(self, tmp_path):
        reg = _make_registry(tmp_path, {"metric": METRIC_YAML})
        layout = reg.get_layout("metric")
        assert layout.constraints.allow_extra_slots is True

    def test_constraints_default_when_absent(self, tmp_path):
        yaml_no_constraints = textwrap.dedent("""\
            schema_version: 1
            layout_id: bare
            version: 1.0.0
            regions:
              content:
                required: true
        """)
        reg = _make_registry(tmp_path, {"bare": yaml_no_constraints})
        layout = reg.get_layout("bare")
        assert layout.constraints.allow_extra_slots is False

    def test_multiple_regions(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        layout = reg.get_layout("two_column")
        assert set(layout.regions) == {"left", "right"}

    def test_returns_layout_definition_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        assert isinstance(layout, LayoutDefinition)

    def test_regions_are_region_definition_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        layout = reg.get_layout("single_column")
        for region in layout.regions.values():
            assert isinstance(region, RegionDefinition)


# ---------------------------------------------------------------------------
# TestGetLayoutErrors
# ---------------------------------------------------------------------------


class TestGetLayoutErrors:
    def test_unknown_layout_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        with pytest.raises(UnknownLayoutError):
            reg.get_layout("nonexistent")

    def test_unknown_layout_error_lists_available(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        with pytest.raises(UnknownLayoutError, match="single_column"):
            reg.get_layout("nonexistent")

    def test_unknown_layout_empty_dir(self, tmp_path):
        (tmp_path / "layouts").mkdir()
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(UnknownLayoutError, match="none"):
            reg.get_layout("any")

    def test_missing_required_key_layout_id(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            version: 1.0.0
            regions:
              content:
                required: true
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidLayoutDefinitionError, match="layout_id"):
            reg.get_layout("bad")

    def test_missing_required_key_regions(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            layout_id: bad
            version: 1.0.0
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidLayoutDefinitionError, match="regions"):
            reg.get_layout("bad")

    def test_regions_not_mapping_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            layout_id: bad
            version: 1.0.0
            regions:
              - content
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidLayoutDefinitionError):
            reg.get_layout("bad")

    def test_region_entry_not_mapping_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            layout_id: bad
            version: 1.0.0
            regions:
              content: "not a mapping"
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidLayoutDefinitionError):
            reg.get_layout("bad")

    def test_malformed_yaml_raises(self, tmp_path):
        layouts_dir = tmp_path / "layouts"
        layouts_dir.mkdir(parents=True)
        (layouts_dir / "broken.yaml").write_text(": invalid: yaml: {\n", encoding="utf-8")
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(InvalidLayoutDefinitionError):
            reg.get_layout("broken")

    def test_constraints_not_mapping_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            layout_id: bad
            version: 1.0.0
            constraints: "wrong"
            regions:
              content:
                required: true
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidLayoutDefinitionError):
            reg.get_layout("bad")


# ---------------------------------------------------------------------------
# TestListLayouts
# ---------------------------------------------------------------------------


class TestListLayouts:
    def test_returns_sorted_list(self, tmp_path):
        reg = _make_registry(tmp_path, {
            "two_column": TWO_COL_YAML,
            "single_column": SINGLE_COL_YAML,
        })
        assert reg.list_layouts() == ["single_column", "two_column"]

    def test_empty_when_dir_missing(self, tmp_path):
        reg = DesignSystemRegistry(tmp_path)
        assert reg.list_layouts() == []

    def test_empty_dir_returns_empty(self, tmp_path):
        (tmp_path / "layouts").mkdir()
        reg = DesignSystemRegistry(tmp_path)
        assert reg.list_layouts() == []

    def test_single_entry(self, tmp_path):
        reg = _make_registry(tmp_path, {"single_column": SINGLE_COL_YAML})
        assert reg.list_layouts() == ["single_column"]


# ---------------------------------------------------------------------------
# TestRealLayoutArtifacts — smoke tests against actual design_system/layouts/
# ---------------------------------------------------------------------------


class TestRealLayoutArtifacts:
    @pytest.fixture
    def real_registry(self):
        root = Path(__file__).parent.parent.parent / "design_system"
        return DesignSystemRegistry(root)

    def test_list_layouts_non_empty(self, real_registry):
        layouts = real_registry.list_layouts()
        assert len(layouts) >= 3

    def test_single_column_loads(self, real_registry):
        layout = real_registry.get_layout("single_column")
        assert layout.layout_id == "single_column"
        assert "content" in layout.regions

    def test_two_column_loads(self, real_registry):
        layout = real_registry.get_layout("two_column")
        assert "left" in layout.regions
        assert "right" in layout.regions

    def test_grid_2x2_loads(self, real_registry):
        layout = real_registry.get_layout("grid_2x2")
        assert len(layout.regions) == 4
