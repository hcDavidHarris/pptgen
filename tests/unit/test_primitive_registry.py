"""Tests for primitive artifact loading in DesignSystemRegistry — Phase 9 Stage 3.

Covers:
- Loading a valid primitive definition
- Slot required/optional flag
- Slot content_type loading
- Slot maps_to loading (explicit and default)
- Slot description
- Constraints loading (allow_extra_content)
- Missing primitive → UnknownPrimitiveError with available list
- Malformed YAML → InvalidPrimitiveDefinitionError
- Missing required key → InvalidPrimitiveDefinitionError
- Non-mapping slots block → InvalidPrimitiveDefinitionError
- Non-mapping slot entry → InvalidPrimitiveDefinitionError
- Unknown content_type → InvalidPrimitiveDefinitionError
- Non-mapping constraints → InvalidPrimitiveDefinitionError
- list_primitives() discovery
- Real design_system/ smoke tests
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pptgen.design_system.exceptions import (
    InvalidPrimitiveDefinitionError,
    UnknownPrimitiveError,
)
from pptgen.design_system.primitive_models import SlidePrimitiveDefinition, SlotDefinition
from pptgen.design_system.registry import DesignSystemRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BULLET_YAML = textwrap.dedent("""\
    schema_version: 1
    primitive_id: bullet_slide
    version: 1.0.0
    layout_id: single_column
    constraints:
      allow_extra_content: false
    slots:
      title:
        required: true
        content_type: string
        maps_to: content
        description: "Slide heading"
      bullets:
        required: true
        content_type: list
        maps_to: content
        description: "Bullet items"
      body:
        required: false
        content_type: string
        maps_to: content
        description: "Optional body text"
""")

COMPARISON_YAML = textwrap.dedent("""\
    schema_version: 1
    primitive_id: comparison_slide
    version: 2.0.0
    layout_id: two_column
    constraints:
      allow_extra_content: true
    slots:
      left:
        required: true
        content_type: dict
        maps_to: left
      right:
        required: true
        content_type: dict
        maps_to: right
""")

MINIMAL_YAML = textwrap.dedent("""\
    schema_version: 1
    primitive_id: minimal
    version: 1.0.0
    layout_id: single_column
    slots:
      content:
        required: true
""")


def _make_registry(tmp_path: Path, primitives: dict[str, str]) -> DesignSystemRegistry:
    prim_dir = tmp_path / "primitives"
    prim_dir.mkdir(parents=True)
    for name, content in primitives.items():
        (prim_dir / f"{name}.yaml").write_text(content, encoding="utf-8")
    return DesignSystemRegistry(tmp_path)


# ---------------------------------------------------------------------------
# TestGetPrimitive — basic loading
# ---------------------------------------------------------------------------


class TestGetPrimitive:
    def test_loads_primitive_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.primitive_id == "bullet_slide"

    def test_loads_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.version == "1.0.0"

    def test_loads_schema_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.schema_version == 1

    def test_loads_layout_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.layout_id == "single_column"

    def test_loads_slots(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert "title" in prim.slots
        assert "bullets" in prim.slots
        assert "body" in prim.slots

    def test_slot_required_true(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.slots["title"].required is True

    def test_slot_required_false(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.slots["body"].required is False

    def test_slot_content_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.slots["bullets"].content_type == "list"

    def test_slot_maps_to(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.slots["title"].maps_to == "content"

    def test_slot_description(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.slots["title"].description == "Slide heading"

    def test_slot_maps_to_defaults_to_slot_name(self, tmp_path):
        reg = _make_registry(tmp_path, {"minimal": MINIMAL_YAML})
        prim = reg.get_primitive("minimal")
        assert prim.slots["content"].maps_to == "content"

    def test_slot_content_type_defaults_to_any(self, tmp_path):
        reg = _make_registry(tmp_path, {"minimal": MINIMAL_YAML})
        prim = reg.get_primitive("minimal")
        assert prim.slots["content"].content_type == "any"

    def test_constraints_allow_extra_content_false(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert prim.constraints.allow_extra_content is False

    def test_constraints_allow_extra_content_true(self, tmp_path):
        reg = _make_registry(tmp_path, {"comparison_slide": COMPARISON_YAML})
        prim = reg.get_primitive("comparison_slide")
        assert prim.constraints.allow_extra_content is True

    def test_constraints_default_when_absent(self, tmp_path):
        reg = _make_registry(tmp_path, {"minimal": MINIMAL_YAML})
        prim = reg.get_primitive("minimal")
        assert prim.constraints.allow_extra_content is False

    def test_returns_primitive_definition_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        assert isinstance(prim, SlidePrimitiveDefinition)

    def test_slots_are_slot_definition_type(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        prim = reg.get_primitive("bullet_slide")
        for slot in prim.slots.values():
            assert isinstance(slot, SlotDefinition)

    def test_multiple_slots(self, tmp_path):
        reg = _make_registry(tmp_path, {"comparison_slide": COMPARISON_YAML})
        prim = reg.get_primitive("comparison_slide")
        assert set(prim.slots) == {"left", "right"}


# ---------------------------------------------------------------------------
# TestGetPrimitiveErrors
# ---------------------------------------------------------------------------


class TestGetPrimitiveErrors:
    def test_unknown_primitive_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(UnknownPrimitiveError):
            reg.get_primitive("nonexistent")

    def test_unknown_primitive_lists_available(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(UnknownPrimitiveError, match="bullet_slide"):
            reg.get_primitive("nonexistent")

    def test_unknown_primitive_empty_dir(self, tmp_path):
        (tmp_path / "primitives").mkdir()
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(UnknownPrimitiveError, match="none"):
            reg.get_primitive("any")

    def test_missing_required_key_primitive_id(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            version: 1.0.0
            layout_id: single_column
            slots:
              content:
                required: true
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidPrimitiveDefinitionError, match="primitive_id"):
            reg.get_primitive("bad")

    def test_missing_required_key_layout_id(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            primitive_id: bad
            version: 1.0.0
            slots:
              content:
                required: true
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidPrimitiveDefinitionError, match="layout_id"):
            reg.get_primitive("bad")

    def test_missing_required_key_slots(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            primitive_id: bad
            version: 1.0.0
            layout_id: single_column
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidPrimitiveDefinitionError, match="slots"):
            reg.get_primitive("bad")

    def test_slots_not_mapping_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            primitive_id: bad
            version: 1.0.0
            layout_id: single_column
            slots:
              - content
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidPrimitiveDefinitionError):
            reg.get_primitive("bad")

    def test_slot_entry_not_mapping_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            primitive_id: bad
            version: 1.0.0
            layout_id: single_column
            slots:
              content: "not a mapping"
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidPrimitiveDefinitionError):
            reg.get_primitive("bad")

    def test_unknown_content_type_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            primitive_id: bad
            version: 1.0.0
            layout_id: single_column
            slots:
              content:
                required: true
                content_type: boolean
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidPrimitiveDefinitionError, match="boolean"):
            reg.get_primitive("bad")

    def test_constraints_not_mapping_raises(self, tmp_path):
        bad = textwrap.dedent("""\
            schema_version: 1
            primitive_id: bad
            version: 1.0.0
            layout_id: single_column
            constraints: "wrong"
            slots:
              content:
                required: true
        """)
        reg = _make_registry(tmp_path, {"bad": bad})
        with pytest.raises(InvalidPrimitiveDefinitionError):
            reg.get_primitive("bad")

    def test_malformed_yaml_raises(self, tmp_path):
        prim_dir = tmp_path / "primitives"
        prim_dir.mkdir(parents=True)
        (prim_dir / "broken.yaml").write_text(": invalid: yaml: {\n", encoding="utf-8")
        reg = DesignSystemRegistry(tmp_path)
        with pytest.raises(InvalidPrimitiveDefinitionError):
            reg.get_primitive("broken")


# ---------------------------------------------------------------------------
# TestListPrimitives
# ---------------------------------------------------------------------------


class TestListPrimitives:
    def test_returns_sorted_list(self, tmp_path):
        reg = _make_registry(tmp_path, {
            "comparison_slide": COMPARISON_YAML,
            "bullet_slide": BULLET_YAML,
        })
        assert reg.list_primitives() == ["bullet_slide", "comparison_slide"]

    def test_empty_when_dir_missing(self, tmp_path):
        reg = DesignSystemRegistry(tmp_path)
        assert reg.list_primitives() == []

    def test_empty_dir_returns_empty(self, tmp_path):
        (tmp_path / "primitives").mkdir()
        reg = DesignSystemRegistry(tmp_path)
        assert reg.list_primitives() == []

    def test_single_entry(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        assert reg.list_primitives() == ["bullet_slide"]


# ---------------------------------------------------------------------------
# TestRealPrimitiveArtifacts — smoke tests against actual design_system/
# ---------------------------------------------------------------------------


class TestRealPrimitiveArtifacts:
    @pytest.fixture
    def real_registry(self):
        root = Path(__file__).parent.parent.parent / "design_system"
        return DesignSystemRegistry(root)

    def test_list_primitives_non_empty(self, real_registry):
        primitives = real_registry.list_primitives()
        assert len(primitives) >= 4

    def test_bullet_slide_loads(self, real_registry):
        prim = real_registry.get_primitive("bullet_slide")
        assert prim.primitive_id == "bullet_slide"
        assert prim.layout_id == "single_column"
        assert "title" in prim.slots
        assert "bullets" in prim.slots

    def test_comparison_slide_loads(self, real_registry):
        prim = real_registry.get_primitive("comparison_slide")
        assert "left" in prim.slots
        assert "right" in prim.slots
        assert prim.layout_id == "two_column"

    def test_metrics_slide_loads(self, real_registry):
        prim = real_registry.get_primitive("metrics_slide")
        assert "headline_metric" in prim.slots
        assert prim.layout_id == "metric_dashboard"

    def test_title_slide_loads(self, real_registry):
        prim = real_registry.get_primitive("title_slide")
        assert "title" in prim.slots
        assert prim.slots["title"].required is True
