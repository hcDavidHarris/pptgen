"""Layout primitive models for the pptgen design system — Phase 9 Stage 2.

Four flat, deterministic artifacts:

* :class:`LayoutConstraints`  — validation rules for slot usage.
* :class:`RegionDefinition`   — a single named content region in a layout.
* :class:`LayoutDefinition`   — a complete layout config artifact loaded from YAML.
* :class:`ResolvedLayout`     — the validated, normalised layout produced at run time.

Layouts define *structure only* — content regions and positioning metadata.
They carry no slide semantics, styling, or token overrides.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LayoutConstraints:
    """Validation rules that govern how slots may be used in a layout.

    Attributes:
        allow_extra_slots: When ``True`` slots that are not declared as regions
            are silently accepted.  When ``False`` (the default) any slot not
            matching a declared region raises :class:`~.exceptions.UnknownSlotError`.
    """

    allow_extra_slots: bool = False


@dataclass(frozen=True)
class RegionDefinition:
    """A single named content region within a layout.

    Attributes:
        name:     Stable region identifier (e.g. ``"left"``, ``"content"``).
        required: When ``True`` the template *must* provide a matching slot.
        label:    Optional human-readable description.
        position: Optional positioning metadata (keys such as ``x``, ``y``,
                  ``width``, ``height`` as percentage strings or point integers).
                  Informational only — not consumed by the renderer in Stage 2.
    """

    name: str
    required: bool = True
    label: str = ""
    position: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LayoutDefinition:
    """A complete layout config artifact loaded from a YAML file.

    Attributes:
        layout_id:      Stable identifier matching the filename stem.
        version:        Artifact version string (e.g. ``"1.0.0"``).
        schema_version: Configuration schema version (integer).
        regions:        Ordered mapping of region name → :class:`RegionDefinition`.
        constraints:    Slot validation rules for this layout.
    """

    layout_id: str
    version: str
    schema_version: int
    regions: dict[str, RegionDefinition]
    constraints: LayoutConstraints


@dataclass(frozen=True)
class ResolvedLayout:
    """Validated, normalised layout produced by :class:`~.layout_resolver.LayoutResolver`.

    Captures the identity of the layout used and the slots that were matched.
    One instance is created per run (when a layout is declared) and stored in
    ``PipelineResult.resolved_layout``.

    Attributes:
        layout_id:      Layout that was resolved.
        layout_version: Version of that layout definition.
        regions:        Region definitions from the layout (full set, not just matched).
        provided_slots: Slot names declared by the template (validated subset).
    """

    layout_id: str
    layout_version: str
    regions: dict[str, RegionDefinition]
    provided_slots: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON persistence."""
        return {
            "layout_id": self.layout_id,
            "layout_version": self.layout_version,
            "regions": {
                name: {
                    "required": r.required,
                    "label": r.label,
                    "position": dict(r.position),
                }
                for name, r in self.regions.items()
            },
            "provided_slots": list(self.provided_slots),
        }
