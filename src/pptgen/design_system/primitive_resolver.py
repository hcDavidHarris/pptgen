"""Primitive resolver — Phase 9 Stage 3.

Validates semantic content fields against a
:class:`~.primitive_models.SlidePrimitiveDefinition` and produces a
deterministic :class:`~.primitive_models.ResolvedSlidePrimitive` that maps
content into layout-region-keyed slots.

Resolution is fail-fast: any constraint violation raises immediately with a
descriptive error.  Silent fallback is prohibited.
"""

from __future__ import annotations

from typing import Any

from .exceptions import (
    InvalidContentTypeError,
    MissingRequiredContentError,
    UnknownContentFieldError,
)
from .primitive_models import ResolvedSlidePrimitive, SlidePrimitiveDefinition
from .registry import DesignSystemRegistry

# ---------------------------------------------------------------------------
# Type-check dispatch table
# ---------------------------------------------------------------------------

def _check_type(content_type: str, value: Any, field_name: str, primitive_id: str) -> None:
    """Raise :class:`~.exceptions.InvalidContentTypeError` when *value* does not
    match *content_type*.  ``"any"`` always passes.
    """
    if content_type == "any":
        return
    if content_type == "string":
        ok = isinstance(value, str)
    elif content_type == "list":
        ok = isinstance(value, list)
    elif content_type == "dict":
        ok = isinstance(value, dict)
    elif content_type == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    else:
        # Unknown types are caught at registry load time; treat as "any" here.
        return
    if not ok:
        raise InvalidContentTypeError(
            f"Primitive '{primitive_id}' field '{field_name}' expects "
            f"content_type '{content_type}' but received "
            f"{type(value).__name__!r}."
        )


class PrimitiveResolver:
    """Validates and resolves primitive content declarations.

    Usage::

        registry = DesignSystemRegistry(settings.design_system_root)
        resolver = PrimitiveResolver()
        resolved = resolver.resolve("bullet_slide", {"title": "...", "bullets": [...]}, registry)
    """

    def resolve(
        self,
        primitive_id: str,
        content: dict[str, Any],
        registry: DesignSystemRegistry,
    ) -> ResolvedSlidePrimitive:
        """Load *primitive_id* and validate *content* against its slot definitions.

        Args:
            primitive_id: ID of the primitive to resolve (must exist in registry).
            content:      Semantic content fields from the template
                          (``deck_definition["content"]``).
            registry:     Loaded :class:`~.registry.DesignSystemRegistry`.

        Returns:
            :class:`~.primitive_models.ResolvedSlidePrimitive` with
            ``layout_id`` and ``resolved_slots`` ready for the layout stage.

        Raises:
            UnknownPrimitiveError:        *primitive_id* not found.
            InvalidPrimitiveDefinitionError: Primitive YAML is malformed.
            MissingRequiredContentError:  A required slot has no matching field.
            UnknownContentFieldError:     A content field is not declared and
                                          ``allow_extra_content`` is ``False``.
            InvalidContentTypeError:      A content field value has the wrong type.
        """
        # Raises UnknownPrimitiveError / InvalidPrimitiveDefinitionError on failure.
        primitive: SlidePrimitiveDefinition = registry.get_primitive(primitive_id)

        # Validate required slots are provided.
        missing = [
            name
            for name, slot in primitive.slots.items()
            if slot.required and name not in content
        ]
        if missing:
            raise MissingRequiredContentError(
                f"Primitive '{primitive_id}' requires content field(s) "
                f"{sorted(missing)} but they were not provided. "
                f"Provided: {sorted(content) or '(none)'}."
            )

        # Validate no unknown content fields (unless explicitly allowed).
        if not primitive.constraints.allow_extra_content:
            unknown = [key for key in content if key not in primitive.slots]
            if unknown:
                raise UnknownContentFieldError(
                    f"Primitive '{primitive_id}' does not define slot(s) "
                    f"{sorted(unknown)}. "
                    f"Defined slots: {sorted(primitive.slots)}."
                )

        # Validate content types for declared fields.
        for field_name, value in content.items():
            if field_name in primitive.slots:
                slot = primitive.slots[field_name]
                _check_type(slot.content_type, value, field_name, primitive_id)

        # Build resolved_slots: group content by target layout region.
        resolved_slots: dict[str, Any] = {}
        for field_name, value in content.items():
            if field_name not in primitive.slots:
                # allow_extra_content=True path: include under field name as region.
                region = field_name
            else:
                region = primitive.slots[field_name].maps_to or field_name
            if region in resolved_slots:
                existing = resolved_slots[region]
                if isinstance(existing, dict):
                    existing[field_name] = value
                else:
                    resolved_slots[region] = {field_name: value}
            else:
                resolved_slots[region] = {field_name: value}

        return ResolvedSlidePrimitive(
            primitive_id=primitive.primitive_id,
            primitive_version=primitive.version,
            layout_id=primitive.layout_id,
            resolved_slots=resolved_slots,
        )
