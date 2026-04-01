"""Layout resolver — Phase 9 Stage 2.

Validates slot declarations against a :class:`~.layout_models.LayoutDefinition`
and produces a deterministic :class:`~.layout_models.ResolvedLayout`.

Resolution is fail-fast: any constraint violation raises immediately with a
descriptive error.  Silent fallback is prohibited.
"""

from __future__ import annotations

from .exceptions import MissingRequiredSlotError, UnknownSlotError
from .layout_models import LayoutDefinition, ResolvedLayout
from .registry import DesignSystemRegistry


class LayoutResolver:
    """Validates and resolves layout slot declarations.

    Usage::

        registry = DesignSystemRegistry(settings.design_system_root)
        resolver = LayoutResolver()
        resolved = resolver.resolve("two_column", ["left", "right"], registry)
    """

    def resolve(
        self,
        layout_id: str,
        provided_slots: list[str],
        registry: DesignSystemRegistry,
    ) -> ResolvedLayout:
        """Load *layout_id* and validate *provided_slots* against it.

        Args:
            layout_id:      ID of the layout to resolve (must exist in registry).
            provided_slots: Slot names declared by the template (order preserved).
            registry:       Loaded :class:`~.registry.DesignSystemRegistry`.

        Returns:
            :class:`~.layout_models.ResolvedLayout` — validated and normalised.

        Raises:
            UnknownLayoutError:        *layout_id* not found in registry.
            InvalidLayoutDefinitionError: Layout YAML is malformed.
            MissingRequiredSlotError:  A required region has no matching slot.
            UnknownSlotError:          A slot does not match any region and
                                       ``allow_extra_slots`` is ``False``.
        """
        # Raises UnknownLayoutError / InvalidLayoutDefinitionError on failure.
        layout: LayoutDefinition = registry.get_layout(layout_id)

        slot_set = set(provided_slots)

        # Validate required regions are satisfied.
        missing = [
            name
            for name, region in layout.regions.items()
            if region.required and name not in slot_set
        ]
        if missing:
            raise MissingRequiredSlotError(
                f"Layout '{layout_id}' requires slot(s) {sorted(missing)} "
                f"but they were not provided. "
                f"Provided: {sorted(slot_set) or '(none)'}."
            )

        # Validate no unknown slots (unless explicitly allowed).
        if not layout.constraints.allow_extra_slots:
            unknown = [s for s in provided_slots if s not in layout.regions]
            if unknown:
                raise UnknownSlotError(
                    f"Layout '{layout_id}' does not define region(s) {sorted(unknown)}. "
                    f"Defined regions: {sorted(layout.regions)}."
                )

        return ResolvedLayout(
            layout_id=layout.layout_id,
            layout_version=layout.version,
            regions=layout.regions,
            provided_slots=list(provided_slots),
        )
