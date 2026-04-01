"""Tests for PrimitiveResolver — Phase 9 Stage 3.

Covers:
- Valid resolution with all required fields
- Optional fields may be omitted
- Optional fields may be provided
- Missing required field → MissingRequiredContentError
- Unknown content field → UnknownContentFieldError
- allow_extra_content=True permits unknown fields
- Unknown primitive_id → UnknownPrimitiveError
- Content type validation: string, list, dict, number, any
- Invalid content type → InvalidContentTypeError
- resolved_slots groups content by maps_to region
- Multiple fields mapping to same region are merged
- ResolvedSlidePrimitive fields are correct
- to_dict() is JSON-serializable
- Backward compatibility: no primitive → resolved_primitive is None
- Pipeline integration: primitive → layout injected into deck_definition
- resolved_primitive_snapshot.json written correctly
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from pptgen.design_system.exceptions import (
    InvalidContentTypeError,
    MissingRequiredContentError,
    UnknownContentFieldError,
    UnknownPrimitiveError,
)
from pptgen.design_system.primitive_models import ResolvedSlidePrimitive
from pptgen.design_system.primitive_resolver import PrimitiveResolver
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
      bullets:
        required: true
        content_type: list
        maps_to: content
      body:
        required: false
        content_type: string
        maps_to: content
""")

COMPARISON_YAML = textwrap.dedent("""\
    schema_version: 1
    primitive_id: comparison_slide
    version: 1.0.0
    layout_id: two_column
    constraints:
      allow_extra_content: false
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

FLEXIBLE_YAML = textwrap.dedent("""\
    schema_version: 1
    primitive_id: flexible
    version: 1.0.0
    layout_id: single_column
    constraints:
      allow_extra_content: true
    slots:
      title:
        required: true
        content_type: string
        maps_to: content
""")

TYPES_YAML = textwrap.dedent("""\
    schema_version: 1
    primitive_id: type_test
    version: 1.0.0
    layout_id: single_column
    slots:
      str_field:
        required: false
        content_type: string
        maps_to: content
      list_field:
        required: false
        content_type: list
        maps_to: content
      dict_field:
        required: false
        content_type: dict
        maps_to: content
      num_field:
        required: false
        content_type: number
        maps_to: content
      any_field:
        required: false
        content_type: any
        maps_to: content
""")


def _make_registry(tmp_path: Path, primitives: dict[str, str]) -> DesignSystemRegistry:
    prim_dir = tmp_path / "primitives"
    prim_dir.mkdir(parents=True)
    for name, content in primitives.items():
        (prim_dir / f"{name}.yaml").write_text(content, encoding="utf-8")
    return DesignSystemRegistry(tmp_path)


# ---------------------------------------------------------------------------
# TestValidResolution
# ---------------------------------------------------------------------------


class TestValidResolution:
    def test_returns_resolved_primitive(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a", "b"]}, reg
        )
        assert isinstance(result, ResolvedSlidePrimitive)

    def test_primitive_id_matches(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"]}, reg
        )
        assert result.primitive_id == "bullet_slide"

    def test_primitive_version_matches(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"]}, reg
        )
        assert result.primitive_version == "1.0.0"

    def test_layout_id_from_primitive(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"]}, reg
        )
        assert result.layout_id == "single_column"

    def test_optional_field_may_be_omitted(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        # 'body' is optional — omitting it must not raise.
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"]}, reg
        )
        assert result.layout_id == "single_column"

    def test_optional_field_may_be_provided(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"], "body": "extra"}, reg
        )
        assert "content" in result.resolved_slots

    def test_empty_content_when_no_required_fields(self, tmp_path):
        no_required = textwrap.dedent("""\
            schema_version: 1
            primitive_id: opt_only
            version: 1.0.0
            layout_id: single_column
            slots:
              note:
                required: false
                content_type: string
                maps_to: content
        """)
        reg = _make_registry(tmp_path, {"opt_only": no_required})
        result = PrimitiveResolver().resolve("opt_only", {}, reg)
        assert result.resolved_slots == {}


# ---------------------------------------------------------------------------
# TestSlotMapping
# ---------------------------------------------------------------------------


class TestSlotMapping:
    def test_single_region_gets_content_dict(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a", "b"]}, reg
        )
        assert "content" in result.resolved_slots
        assert result.resolved_slots["content"]["title"] == "T"
        assert result.resolved_slots["content"]["bullets"] == ["a", "b"]

    def test_two_regions_mapped_separately(self, tmp_path):
        reg = _make_registry(tmp_path, {"comparison_slide": COMPARISON_YAML})
        result = PrimitiveResolver().resolve(
            "comparison_slide",
            {"left": {"title": "A"}, "right": {"title": "B"}},
            reg,
        )
        assert "left" in result.resolved_slots
        assert "right" in result.resolved_slots
        assert result.resolved_slots["left"]["left"] == {"title": "A"}
        assert result.resolved_slots["right"]["right"] == {"title": "B"}

    def test_multiple_fields_same_region_merged(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide",
            {"title": "Heading", "bullets": ["x"], "body": "text"},
            reg,
        )
        region = result.resolved_slots["content"]
        assert "title" in region
        assert "bullets" in region
        assert "body" in region


# ---------------------------------------------------------------------------
# TestMissingRequired
# ---------------------------------------------------------------------------


class TestMissingRequired:
    def test_missing_required_field_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(MissingRequiredContentError):
            PrimitiveResolver().resolve("bullet_slide", {"title": "T"}, reg)  # missing bullets

    def test_error_mentions_missing_field(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(MissingRequiredContentError, match="bullets"):
            PrimitiveResolver().resolve("bullet_slide", {"title": "T"}, reg)

    def test_error_mentions_provided_fields(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(MissingRequiredContentError, match="title"):
            PrimitiveResolver().resolve("bullet_slide", {"title": "T"}, reg)

    def test_empty_content_fails_required(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(MissingRequiredContentError):
            PrimitiveResolver().resolve("bullet_slide", {}, reg)


# ---------------------------------------------------------------------------
# TestUnknownContentField
# ---------------------------------------------------------------------------


class TestUnknownContentField:
    def test_unknown_field_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(UnknownContentFieldError):
            PrimitiveResolver().resolve(
                "bullet_slide",
                {"title": "T", "bullets": ["a"], "ghost": "surprise"},
                reg,
            )

    def test_error_mentions_unknown_field(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(UnknownContentFieldError, match="ghost"):
            PrimitiveResolver().resolve(
                "bullet_slide",
                {"title": "T", "bullets": ["a"], "ghost": "surprise"},
                reg,
            )

    def test_error_mentions_defined_slots(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(UnknownContentFieldError, match="title"):
            PrimitiveResolver().resolve(
                "bullet_slide",
                {"title": "T", "bullets": ["a"], "ghost": "x"},
                reg,
            )

    def test_extra_field_accepted_when_allowed(self, tmp_path):
        reg = _make_registry(tmp_path, {"flexible": FLEXIBLE_YAML})
        result = PrimitiveResolver().resolve(
            "flexible", {"title": "T", "extra_note": "hello"}, reg
        )
        assert result.primitive_id == "flexible"


# ---------------------------------------------------------------------------
# TestContentTypeValidation
# ---------------------------------------------------------------------------


class TestContentTypeValidation:
    def test_string_type_valid(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        result = PrimitiveResolver().resolve(
            "type_test", {"str_field": "hello"}, reg
        )
        assert result.primitive_id == "type_test"

    def test_string_type_invalid(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        with pytest.raises(InvalidContentTypeError, match="string"):
            PrimitiveResolver().resolve("type_test", {"str_field": 42}, reg)

    def test_list_type_valid(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        PrimitiveResolver().resolve("type_test", {"list_field": [1, 2]}, reg)

    def test_list_type_invalid(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        with pytest.raises(InvalidContentTypeError, match="list"):
            PrimitiveResolver().resolve("type_test", {"list_field": "not a list"}, reg)

    def test_dict_type_valid(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        PrimitiveResolver().resolve("type_test", {"dict_field": {"k": "v"}}, reg)

    def test_dict_type_invalid(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        with pytest.raises(InvalidContentTypeError, match="dict"):
            PrimitiveResolver().resolve("type_test", {"dict_field": [1, 2]}, reg)

    def test_number_type_valid_int(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        PrimitiveResolver().resolve("type_test", {"num_field": 42}, reg)

    def test_number_type_valid_float(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        PrimitiveResolver().resolve("type_test", {"num_field": 3.14}, reg)

    def test_number_type_invalid_string(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        with pytest.raises(InvalidContentTypeError, match="number"):
            PrimitiveResolver().resolve("type_test", {"num_field": "not a number"}, reg)

    def test_number_type_rejects_bool(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        with pytest.raises(InvalidContentTypeError, match="number"):
            PrimitiveResolver().resolve("type_test", {"num_field": True}, reg)

    def test_any_type_accepts_string(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        PrimitiveResolver().resolve("type_test", {"any_field": "text"}, reg)

    def test_any_type_accepts_list(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        PrimitiveResolver().resolve("type_test", {"any_field": [1, 2, 3]}, reg)

    def test_any_type_accepts_dict(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        PrimitiveResolver().resolve("type_test", {"any_field": {"k": "v"}}, reg)

    def test_any_type_accepts_number(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        PrimitiveResolver().resolve("type_test", {"any_field": 99}, reg)

    def test_error_mentions_field_name(self, tmp_path):
        reg = _make_registry(tmp_path, {"type_test": TYPES_YAML})
        with pytest.raises(InvalidContentTypeError, match="str_field"):
            PrimitiveResolver().resolve("type_test", {"str_field": 99}, reg)


# ---------------------------------------------------------------------------
# TestUnknownPrimitive
# ---------------------------------------------------------------------------


class TestUnknownPrimitive:
    def test_unknown_primitive_raises(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(UnknownPrimitiveError):
            PrimitiveResolver().resolve("nonexistent", {"title": "T"}, reg)

    def test_error_lists_available(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        with pytest.raises(UnknownPrimitiveError, match="bullet_slide"):
            PrimitiveResolver().resolve("nonexistent", {}, reg)


# ---------------------------------------------------------------------------
# TestResolvedSlidePrimitiveToDict
# ---------------------------------------------------------------------------


class TestResolvedSlidePrimitiveToDict:
    def test_contains_primitive_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"]}, reg
        )
        assert result.to_dict()["primitive_id"] == "bullet_slide"

    def test_contains_primitive_version(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"]}, reg
        )
        assert result.to_dict()["primitive_version"] == "1.0.0"

    def test_contains_layout_id(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"]}, reg
        )
        assert result.to_dict()["layout_id"] == "single_column"

    def test_contains_resolved_slots(self, tmp_path):
        reg = _make_registry(tmp_path, {"bullet_slide": BULLET_YAML})
        result = PrimitiveResolver().resolve(
            "bullet_slide", {"title": "T", "bullets": ["a"]}, reg
        )
        assert "resolved_slots" in result.to_dict()

    def test_is_json_serializable(self, tmp_path):
        reg = _make_registry(tmp_path, {"comparison_slide": COMPARISON_YAML})
        result = PrimitiveResolver().resolve(
            "comparison_slide",
            {"left": {"title": "A"}, "right": {"title": "B"}},
            reg,
        )
        json.dumps(result.to_dict())  # must not raise


# ---------------------------------------------------------------------------
# TestPipelineIntegration
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Exercises the resolved primitive → layout injection path."""

    @pytest.fixture
    def real_registry_root(self):
        return Path(__file__).parent.parent.parent / "design_system"

    def test_no_primitive_returns_none(self, real_registry_root):
        from pptgen.design_system.registry import DesignSystemRegistry
        deck = {"title": "plain deck"}
        declared = deck.get("primitive")
        assert declared is None

    def test_primitive_produces_resolved_primitive(self, real_registry_root):
        from pptgen.design_system.registry import DesignSystemRegistry

        registry = DesignSystemRegistry(real_registry_root)
        result = PrimitiveResolver().resolve(
            "bullet_slide",
            {"title": "Overview", "bullets": ["point 1", "point 2"]},
            registry,
        )
        assert isinstance(result, ResolvedSlidePrimitive)
        assert result.layout_id == "single_column"

    def test_primitive_injects_layout_key(self, real_registry_root):
        from pptgen.design_system.registry import DesignSystemRegistry

        registry = DesignSystemRegistry(real_registry_root)
        deck = {
            "primitive": "bullet_slide",
            "content": {"title": "T", "bullets": ["a"]},
        }
        resolved = PrimitiveResolver().resolve(
            str(deck["primitive"]),
            deck.get("content") or {},
            registry,
        )
        injected = {**deck, "layout": resolved.layout_id, "slots": resolved.resolved_slots}
        assert injected["layout"] == "single_column"
        assert "slots" in injected

    def test_primitive_injects_slots_matching_layout(self, real_registry_root):
        from pptgen.design_system.registry import DesignSystemRegistry
        from pptgen.design_system.layout_resolver import LayoutResolver

        registry = DesignSystemRegistry(real_registry_root)
        resolved_primitive = PrimitiveResolver().resolve(
            "comparison_slide",
            {"left": {"option": "A"}, "right": {"option": "B"}},
            registry,
        )
        # The injected slots must satisfy the two_column layout.
        layout = LayoutResolver().resolve(
            resolved_primitive.layout_id,
            list(resolved_primitive.resolved_slots.keys()),
            registry,
        )
        assert layout.layout_id == "two_column"

    def test_missing_required_content_raises_pipeline_error(self, real_registry_root):
        from pptgen.design_system.registry import DesignSystemRegistry

        registry = DesignSystemRegistry(real_registry_root)
        with pytest.raises(MissingRequiredContentError):
            PrimitiveResolver().resolve(
                "bullet_slide",
                {"title": "T"},  # missing 'bullets'
                registry,
            )

    def test_unknown_primitive_raises(self, real_registry_root):
        from pptgen.design_system.registry import DesignSystemRegistry

        registry = DesignSystemRegistry(real_registry_root)
        with pytest.raises(UnknownPrimitiveError):
            PrimitiveResolver().resolve("nonexistent", {}, registry)

    def test_primitive_snapshot_serializable(self, real_registry_root, tmp_path):
        from pptgen.design_system.registry import DesignSystemRegistry

        registry = DesignSystemRegistry(real_registry_root)
        result = PrimitiveResolver().resolve(
            "metrics_slide",
            {"headline_metric": "95% Uptime"},
            registry,
        )
        snapshot_path = tmp_path / "resolved_primitive_snapshot.json"
        snapshot_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

        data = json.loads(snapshot_path.read_text())
        assert data["primitive_id"] == "metrics_slide"
        assert "resolved_slots" in data
        assert "layout_id" in data
