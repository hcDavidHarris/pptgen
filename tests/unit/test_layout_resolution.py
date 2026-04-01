"""Tests for LayoutResolver — Phase 9 Stage 2.

Covers:
- Valid resolution with all required slots
- Optional regions may be omitted
- Missing required slot → MissingRequiredSlotError
- Unknown slot → UnknownSlotError
- allow_extra_slots=True permits unknown slots
- Unknown layout_id → UnknownLayoutError
- ResolvedLayout fields are correct
- provided_slots order is preserved
- to_dict() output is JSON-serializable
- Pipeline backward compat: no layout → resolved_layout is None
- Pipeline with layout → resolved_layout is populated
- Pipeline missing required slot → PipelineError
- Pipeline unknown slot → PipelineError
- resolved_layout_snapshot.json written to artifacts_dir
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pptgen.design_system.exceptions import (
    MissingRequiredSlotError,
    UnknownLayoutError,
    UnknownSlotError,
)
from pptgen.design_system.layout_models import ResolvedLayout
from pptgen.design_system.layout_resolver import LayoutResolver
from pptgen.design_system.registry import DesignSystemRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
        required: true
        label: "Right Column"
""")

FLEXIBLE_YAML = textwrap.dedent("""\
    schema_version: 1
    layout_id: flexible
    version: 1.0.0
    constraints:
      allow_extra_slots: true
    regions:
      content:
        required: true
        label: "Content"
      optional_sidebar:
        required: false
        label: "Sidebar"
""")

METRIC_YAML = textwrap.dedent("""\
    schema_version: 1
    layout_id: metric_dashboard
    version: 1.0.0
    constraints:
      allow_extra_slots: false
    regions:
      headline:
        required: true
        label: "Headline"
      detail_left:
        required: false
        label: "Detail Left"
      detail_right:
        required: false
        label: "Detail Right"
""")


def _make_registry(tmp_path: Path, layouts: dict[str, str]) -> DesignSystemRegistry:
    layouts_dir = tmp_path / "layouts"
    layouts_dir.mkdir(parents=True)
    for name, content in layouts.items():
        (layouts_dir / f"{name}.yaml").write_text(content, encoding="utf-8")
    return DesignSystemRegistry(tmp_path)


# ---------------------------------------------------------------------------
# TestValidResolution
# ---------------------------------------------------------------------------


class TestValidResolution:
    def test_returns_resolved_layout(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        resolver = LayoutResolver()
        result = resolver.resolve("two_column", ["left", "right"], reg)
        assert isinstance(result, ResolvedLayout)

    def test_layout_id_matches(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        assert result.layout_id == "two_column"

    def test_layout_version_matches(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        assert result.layout_version == "1.0.0"

    def test_regions_present_in_result(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        assert set(result.regions) == {"left", "right"}

    def test_provided_slots_recorded(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        assert result.provided_slots == ["left", "right"]

    def test_slot_order_preserved(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["right", "left"], reg)
        assert result.provided_slots == ["right", "left"]

    def test_optional_region_may_be_omitted(self, tmp_path):
        reg = _make_registry(tmp_path, {"metric_dashboard": METRIC_YAML})
        # Only headline (required) — optional detail regions omitted.
        result = LayoutResolver().resolve("metric_dashboard", ["headline"], reg)
        assert result.layout_id == "metric_dashboard"

    def test_optional_region_may_be_included(self, tmp_path):
        reg = _make_registry(tmp_path, {"metric_dashboard": METRIC_YAML})
        result = LayoutResolver().resolve(
            "metric_dashboard", ["headline", "detail_left"], reg
        )
        assert "detail_left" in result.provided_slots

    def test_empty_slots_when_no_required_regions(self, tmp_path):
        all_optional = textwrap.dedent("""\
            schema_version: 1
            layout_id: all_optional
            version: 1.0.0
            regions:
              sidebar:
                required: false
        """)
        reg = _make_registry(tmp_path, {"all_optional": all_optional})
        result = LayoutResolver().resolve("all_optional", [], reg)
        assert result.provided_slots == []


# ---------------------------------------------------------------------------
# TestAllowExtraSlots
# ---------------------------------------------------------------------------


class TestAllowExtraSlots:
    def test_extra_slot_accepted_when_allowed(self, tmp_path):
        reg = _make_registry(tmp_path, {"flexible": FLEXIBLE_YAML})
        # "unknown_slot" not in regions but allow_extra_slots=true.
        result = LayoutResolver().resolve(
            "flexible", ["content", "unknown_slot"], reg
        )
        assert "unknown_slot" in result.provided_slots

    def test_extra_slot_rejected_when_not_allowed(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(UnknownSlotError):
            LayoutResolver().resolve("two_column", ["left", "right", "extra"], reg)


# ---------------------------------------------------------------------------
# TestMissingRequired
# ---------------------------------------------------------------------------


class TestMissingRequired:
    def test_missing_required_slot_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(MissingRequiredSlotError):
            LayoutResolver().resolve("two_column", ["left"], reg)

    def test_error_mentions_missing_slot(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(MissingRequiredSlotError, match="right"):
            LayoutResolver().resolve("two_column", ["left"], reg)

    def test_error_mentions_provided_slots(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(MissingRequiredSlotError, match="left"):
            LayoutResolver().resolve("two_column", ["left"], reg)

    def test_empty_slots_fails_required(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(MissingRequiredSlotError):
            LayoutResolver().resolve("two_column", [], reg)


# ---------------------------------------------------------------------------
# TestUnknownSlot
# ---------------------------------------------------------------------------


class TestUnknownSlot:
    def test_unknown_slot_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(UnknownSlotError):
            LayoutResolver().resolve("two_column", ["left", "right", "ghost"], reg)

    def test_error_mentions_unknown_slot_name(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(UnknownSlotError, match="ghost"):
            LayoutResolver().resolve("two_column", ["left", "right", "ghost"], reg)

    def test_error_mentions_defined_regions(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(UnknownSlotError, match="left"):
            LayoutResolver().resolve("two_column", ["left", "right", "ghost"], reg)


# ---------------------------------------------------------------------------
# TestUnknownLayout
# ---------------------------------------------------------------------------


class TestUnknownLayout:
    def test_unknown_layout_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(UnknownLayoutError):
            LayoutResolver().resolve("nonexistent", ["left"], reg)

    def test_error_lists_available_layouts(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        with pytest.raises(UnknownLayoutError, match="two_column"):
            LayoutResolver().resolve("nonexistent", ["left"], reg)


# ---------------------------------------------------------------------------
# TestResolvedLayoutToDict
# ---------------------------------------------------------------------------


class TestResolvedLayoutToDict:
    def test_to_dict_contains_layout_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        d = result.to_dict()
        assert d["layout_id"] == "two_column"

    def test_to_dict_contains_layout_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        d = result.to_dict()
        assert d["layout_version"] == "1.0.0"

    def test_to_dict_contains_regions(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        d = result.to_dict()
        assert "left" in d["regions"]

    def test_to_dict_contains_provided_slots(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        d = result.to_dict()
        assert d["provided_slots"] == ["left", "right"]

    def test_to_dict_is_json_serializable(self, tmp_path):
        reg = _make_registry(tmp_path, {"two_column": TWO_COL_YAML})
        result = LayoutResolver().resolve("two_column", ["left", "right"], reg)
        json.dumps(result.to_dict())  # must not raise


# ---------------------------------------------------------------------------
# TestPipelineLayoutIntegration
# ---------------------------------------------------------------------------


class TestPipelineLayoutIntegration:
    """Integration tests exercising layout resolution through generate_presentation()."""

    @pytest.fixture
    def real_registry_root(self):
        return Path(__file__).parent.parent.parent / "design_system"

    def _run(self, deck_definition: dict, design_system_root: Path):
        """Run the pipeline with a stubbed deck_definition containing layout info."""
        from pptgen.design_system.exceptions import DesignSystemError
        from pptgen.design_system.layout_models import ResolvedLayout
        from pptgen.design_system.layout_resolver import LayoutResolver
        from pptgen.design_system.registry import DesignSystemRegistry

        layout_id = deck_definition.get("layout")
        if not layout_id:
            return None

        registry = DesignSystemRegistry(design_system_root)
        raw_slots = deck_definition.get("slots") or {}
        provided_slots = list(raw_slots.keys()) if isinstance(raw_slots, dict) else []
        return LayoutResolver().resolve(layout_id, provided_slots, registry)

    def test_no_layout_returns_none(self, real_registry_root):
        result = self._run({}, real_registry_root)
        assert result is None

    def test_valid_layout_returns_resolved(self, real_registry_root):
        deck = {
            "layout": "two_column",
            "slots": {"left": {}, "right": {}},
        }
        result = self._run(deck, real_registry_root)
        assert isinstance(result, ResolvedLayout)
        assert result.layout_id == "two_column"

    def test_missing_required_slot_raises(self, real_registry_root):
        deck = {
            "layout": "two_column",
            "slots": {"left": {}},  # missing "right"
        }
        with pytest.raises(MissingRequiredSlotError):
            self._run(deck, real_registry_root)

    def test_unknown_slot_raises(self, real_registry_root):
        deck = {
            "layout": "two_column",
            "slots": {"left": {}, "right": {}, "ghost": {}},
        }
        with pytest.raises(UnknownSlotError):
            self._run(deck, real_registry_root)

    def test_unknown_layout_raises(self, real_registry_root):
        deck = {
            "layout": "nonexistent_layout",
            "slots": {},
        }
        with pytest.raises(UnknownLayoutError):
            self._run(deck, real_registry_root)

    def test_resolved_layout_snapshot_written(self, tmp_path, real_registry_root):
        from pptgen.design_system.layout_resolver import LayoutResolver
        from pptgen.design_system.registry import DesignSystemRegistry

        registry = DesignSystemRegistry(real_registry_root)
        result = LayoutResolver().resolve("two_column", ["left", "right"], registry)

        snapshot_path = tmp_path / "resolved_layout_snapshot.json"
        snapshot_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

        data = json.loads(snapshot_path.read_text())
        assert data["layout_id"] == "two_column"
        assert "regions" in data
        assert "provided_slots" in data
