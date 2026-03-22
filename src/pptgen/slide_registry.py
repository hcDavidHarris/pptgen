"""Slide type registry.

Central metadata store for all supported pptgen slide types.

Each entry defines:
  - required_fields:  fields that must be present (beyond `type`)
  - optional_fields:  fields that may be present
  - max_items:        content length limits (label → max count)
  - layout_name:      the PowerPoint layout name this type maps to
  - placeholders:     UPPERCASE_SNAKE_CASE placeholder names required in the layout

This registry is the single source of truth consulted by:
  - validators (deck_validator.py)
  - renderers  (deck_renderer.py, slide_renderers.py)
  - CLI commands (scaffold, template_inspect)
  - documentation generators

To add a new slide type:
  1. Add an entry here.
  2. Add a Pydantic model in models/slides.py and include it in SlideUnion.
  3. Add a renderer function in render/slide_renderers.py and register it in SLIDE_RENDERERS.
  4. Add the layout mapping to render/deck_renderer.py (SLIDE_TYPE_TO_LAYOUT and _SLIDE_TYPE_PH_NAMES).
  5. Add the layout to the template .pptx file.
  6. Update templates/registry.yaml supported_slide_types.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SlideTypeSpec:
    """Metadata for a single registered slide type.

    Attributes:
        type_name:      The `type` discriminator string used in YAML.
        required_fields: Fields that must be present (not including `type`).
        optional_fields: Fields that may be present.
        max_items:      Dict of field_name → max item count (for array fields).
        layout_name:    Canonical PowerPoint layout name in the template.
        placeholders:   UPPERCASE_SNAKE_CASE placeholder names the layout must provide.
        description:    Human-readable description of the slide type.
    """

    type_name: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    max_items: dict[str, int]
    layout_name: str
    placeholders: tuple[str, ...]
    description: str


#: Base optional fields shared by every slide type.
_BASE_OPTIONAL: tuple[str, ...] = ("id", "notes", "visible")


#: Registry of all supported slide types.
#: Add new entries here when adding new slide types.
SLIDE_TYPE_REGISTRY: dict[str, SlideTypeSpec] = {
    "title": SlideTypeSpec(
        type_name="title",
        required_fields=("title", "subtitle"),
        optional_fields=_BASE_OPTIONAL,
        max_items={},
        layout_name="Title Layout",
        placeholders=("TITLE", "SUBTITLE"),
        description="Opening title slide. Should be the first slide in the deck.",
    ),
    "section": SlideTypeSpec(
        type_name="section",
        required_fields=("section_title",),
        optional_fields=("section_subtitle",) + _BASE_OPTIONAL,
        max_items={},
        layout_name="Section Layout",
        placeholders=("SECTION_TITLE", "SECTION_SUBTITLE"),
        description="Section divider slide. Marks the start of a logical group of content slides.",
    ),
    "bullets": SlideTypeSpec(
        type_name="bullets",
        required_fields=("title", "bullets"),
        optional_fields=_BASE_OPTIONAL,
        max_items={"bullets": 6},
        layout_name="Bullets Layout",
        placeholders=("TITLE", "BULLETS"),
        description=(
            "Standard content slide with a bullet list. "
            "Recommended maximum 6 bullets per slide."
        ),
    ),
    "two_column": SlideTypeSpec(
        type_name="two_column",
        required_fields=("title", "left_content", "right_content"),
        optional_fields=_BASE_OPTIONAL,
        max_items={"left_content": 6, "right_content": 6},
        layout_name="Two Column Layout",
        placeholders=("TITLE", "LEFT_CONTENT", "RIGHT_CONTENT"),
        description=(
            "Side-by-side comparison slide. Use for current vs. future state, "
            "pros vs. cons, or functional splits."
        ),
    ),
    "metric_summary": SlideTypeSpec(
        type_name="metric_summary",
        required_fields=("title", "metrics"),
        optional_fields=_BASE_OPTIONAL,
        max_items={"metrics": 4},
        layout_name="Metric Summary Layout",
        placeholders=(
            "TITLE",
            "METRIC_1_LABEL", "METRIC_1_VALUE",
            "METRIC_2_LABEL", "METRIC_2_VALUE",
            "METRIC_3_LABEL", "METRIC_3_VALUE",
            "METRIC_4_LABEL", "METRIC_4_VALUE",
        ),
        description=(
            "KPI overview slide displaying up to 4 metrics in a 2×2 grid. "
            "Hard limit: 4 metrics per slide."
        ),
    ),
    "image_caption": SlideTypeSpec(
        type_name="image_caption",
        required_fields=("title", "image_path", "caption"),
        optional_fields=_BASE_OPTIONAL,
        max_items={},
        layout_name="Image Caption Layout",
        placeholders=("TITLE", "IMAGE", "CAPTION"),
        description=(
            "Image or diagram slide with a title and caption. "
            "Supports PNG and JPEG image formats."
        ),
    ),
}


def get_spec(type_name: str) -> SlideTypeSpec | None:
    """Return the SlideTypeSpec for *type_name*, or None if not registered."""
    return SLIDE_TYPE_REGISTRY.get(type_name)


def all_type_names() -> list[str]:
    """Return a sorted list of all registered slide type names."""
    return sorted(SLIDE_TYPE_REGISTRY.keys())


def all_layout_names() -> list[str]:
    """Return the list of PowerPoint layout names required across all slide types."""
    return [spec.layout_name for spec in SLIDE_TYPE_REGISTRY.values()]


def all_placeholders_for_layout(layout_name: str) -> tuple[str, ...]:
    """Return the placeholder names required for a given layout name.

    Returns an empty tuple if the layout name is not registered.
    """
    for spec in SLIDE_TYPE_REGISTRY.values():
        if spec.layout_name == layout_name:
            return spec.placeholders
    return ()
