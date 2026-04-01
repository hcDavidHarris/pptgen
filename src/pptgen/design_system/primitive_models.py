"""Slide component primitive models for the pptgen design system — Phase 9 Stage 3.

Four flat, deterministic artifacts:

* :class:`PrimitiveConstraints`   — validation rules for content field usage.
* :class:`SlotDefinition`         — a single named semantic content field in a primitive.
* :class:`SlidePrimitiveDefinition` — a complete primitive config artifact loaded from YAML.
* :class:`ResolvedSlidePrimitive` — the validated, normalised primitive produced at run time.

Primitives define *semantic slide intent* — they map named content fields to layout regions.
They carry no styling, token overrides, or renderer logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Supported content field types for declarative validation.
#: ``"any"`` disables type checking for that field.
VALID_CONTENT_TYPES = frozenset({"string", "list", "dict", "number", "any"})


@dataclass(frozen=True)
class PrimitiveConstraints:
    """Validation rules that govern how content fields may be used in a primitive.

    Attributes:
        allow_extra_content: When ``True`` content fields not declared in
            ``slots`` are silently accepted.  When ``False`` (the default)
            any undeclared field raises :class:`~.exceptions.UnknownContentFieldError`.
    """

    allow_extra_content: bool = False


@dataclass(frozen=True)
class SlotDefinition:
    """A single named semantic content field within a primitive.

    Attributes:
        name:         Stable field identifier (e.g. ``"title"``, ``"bullets"``).
        required:     When ``True`` the template *must* provide this field.
        content_type: Expected Python type as a string token — one of
                      ``"string"``, ``"list"``, ``"dict"``, ``"number"``, ``"any"``.
        maps_to:      Layout region name this field's value is placed into.
        description:  Optional human-readable description.
    """

    name: str
    required: bool = True
    content_type: str = "any"
    maps_to: str = ""
    description: str = ""


@dataclass(frozen=True)
class SlidePrimitiveDefinition:
    """A complete primitive config artifact loaded from a YAML file.

    Attributes:
        primitive_id:   Stable identifier matching the filename stem.
        version:        Artifact version string (e.g. ``"1.0.0"``).
        schema_version: Configuration schema version (integer).
        layout_id:      Layout this primitive resolves to.
        slots:          Mapping of content field name → :class:`SlotDefinition`.
        constraints:    Content validation rules for this primitive.
    """

    primitive_id: str
    version: str
    schema_version: int
    layout_id: str
    slots: dict[str, SlotDefinition]
    constraints: PrimitiveConstraints


@dataclass(frozen=True)
class ResolvedSlidePrimitive:
    """Validated, normalised primitive produced by :class:`~.primitive_resolver.PrimitiveResolver`.

    Captures the identity of the primitive used and the layout-ready slot
    mapping derived from the template's content fields.  One instance is
    created per run (when a primitive is declared) and stored in
    ``PipelineResult.resolved_primitive``.

    Attributes:
        primitive_id:     Primitive that was resolved.
        primitive_version: Version of that primitive definition.
        layout_id:        Layout ID this primitive maps to.
        resolved_slots:   Content grouped by layout region —
                          ``{region_name: {field_name: value, ...}}``.
                          This dict is injected as ``deck_definition["slots"]``
                          before the layout resolution stage.
    """

    primitive_id: str
    primitive_version: str
    layout_id: str
    resolved_slots: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON persistence."""
        return {
            "primitive_id": self.primitive_id,
            "primitive_version": self.primitive_version,
            "layout_id": self.layout_id,
            "resolved_slots": {
                region: dict(fields) if isinstance(fields, dict) else fields
                for region, fields in self.resolved_slots.items()
            },
        }
