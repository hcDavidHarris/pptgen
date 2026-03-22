"""Deck renderer.

Orchestrates the full rendering pipeline for a DeckFile:

1. Load the .pptx template from disk.
2. Inspect the template to discover layout names.
3. Iterate the deck's slides in order.
4. For each slide, select the correct SlideLayout by name.
5. Add the slide to the presentation.
6. Dispatch to the appropriate slide renderer via SLIDE_RENDERERS.
7. Save the presentation to the output path.

This module knows nothing about individual slide types — all type-specific
logic lives in slide_renderers.py and is reached through the registry.
"""

from __future__ import annotations

import copy
from pathlib import Path

from lxml import etree

from ..models.deck import DeckFile
from ..slide_registry import SLIDE_TYPE_REGISTRY
from .slide_renderers import SLIDE_RENDERERS
from .template_inspector import inspect_template
from .template_loader import load_template


#: Maps slide type string → canonical layout name in the template.
#: Derived from SLIDE_TYPE_REGISTRY — do not edit this dict directly.
#: Add or change layout names in slide_registry.py instead.
SLIDE_TYPE_TO_LAYOUT: dict[str, str] = {
    type_name: spec.layout_name
    for type_name, spec in SLIDE_TYPE_REGISTRY.items()
}

#: Maps slide type → {placeholder_format.idx: canonical_name}.
#:
#: When python-pptx clones placeholder shapes from a layout to a new slide it
#: auto-generates names like "Title 1" or "Text Placeholder 2".  The canonical
#: names (TITLE, BULLETS, …) defined in the Template Authoring Standard are not
#: preserved.  This mapping is used to rename the shapes immediately after
#: add_slide() so that placeholder_mapper.find_placeholder() can locate them.
#:
#: idx values are determined by the branded template
#: (template/HC_Powerpoint_Template_with_pptgen_placeholders.potx).
_SLIDE_TYPE_PH_NAMES: dict[str, dict[int, str]] = {
    "title": {0: "TITLE", 11: "SUBTITLE"},
    "section": {0: "SECTION_TITLE", 10: "SECTION_SUBTITLE"},
    "bullets": {0: "TITLE", 1: "BULLETS"},
    "two_column": {0: "TITLE", 1: "LEFT_CONTENT", 13: "RIGHT_CONTENT"},
    "metric_summary": {
        0: "TITLE",
        21: "METRIC_1_LABEL", 22: "METRIC_1_VALUE",
        23: "METRIC_2_LABEL", 24: "METRIC_2_VALUE",
        25: "METRIC_3_LABEL", 26: "METRIC_3_VALUE",
        27: "METRIC_4_LABEL", 28: "METRIC_4_VALUE",
    },
    "image_caption": {10: "IMAGE", 21: "TITLE", 22: "CAPTION"},
}


_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _rename_slide_placeholders(slide, slide_type: str) -> None:
    """Rename cloned placeholder shapes to their canonical pptgen names."""
    ph_names = _SLIDE_TYPE_PH_NAMES.get(slide_type, {})
    for shape in slide.shapes:
        pf = getattr(shape, "placeholder_format", None)
        if pf is not None and pf.idx in ph_names:
            shape.name = ph_names[pf.idx]


def _copy_layout_lstStyles(slide, layout) -> None:
    """Copy non-empty lstStyle elements from layout placeholders to slide placeholders.

    When python-pptx clones a placeholder from a layout to a slide, the slide
    placeholder's <a:lstStyle/> is always empty.  PowerPoint resolves text colour
    by walking up the inheritance chain: slide → layout → slide master.  If the
    slide master's bodyStyle declares a light (bg1) body text colour (intended for
    dark-background layouts), text on light-background slides becomes invisible.

    Copying the layout's lstStyle explicitly into the slide placeholder ensures the
    correct colour is present on the slide itself and is not overridden by the master.
    """
    def _ph_idx(shape) -> int | None:
        """Return placeholder idx, or None if shape is not a placeholder."""
        try:
            return shape.placeholder_format.idx
        except (ValueError, AttributeError):
            return None

    # Build a map of idx → <a:lstStyle> from layout placeholder shapes
    layout_styles: dict[int, etree._Element] = {}
    for shape in layout.shapes:
        idx = _ph_idx(shape)
        if idx is None:
            continue
        lst = shape._element.find(f".//{{{_A}}}lstStyle")
        if lst is not None and len(lst) > 0:
            layout_styles[idx] = lst

    if not layout_styles:
        return

    for shape in slide.shapes:
        idx = _ph_idx(shape)
        if idx is None or idx not in layout_styles:
            continue
        slide_lst = shape._element.find(f".//{{{_A}}}lstStyle")
        if slide_lst is None:
            continue
        # Clear then deep-copy each child from the layout lstStyle
        for child in list(slide_lst):
            slide_lst.remove(child)
        for child in layout_styles[idx]:
            slide_lst.append(copy.deepcopy(child))


def render_deck(deck: DeckFile, template_path: Path, output_path: Path) -> None:
    """Render *deck* into a .pptx file at *output_path*.

    Args:
        deck:          Parsed and validated DeckFile model.
        template_path: Path to the .pptx template file.
        output_path:   Destination path for the rendered .pptx.

    Raises:
        TemplateLoadError:          if the template file cannot be opened.
        TemplateCompatibilityError: if a required layout or placeholder is
                                    missing from the template.
        KeyError:                   if a slide type has no registered renderer
                                    (should not happen for validated decks).
    """
    prs = load_template(template_path)
    inspection = inspect_template(prs)

    for slide_model in deck.slides:
        if not slide_model.visible:
            continue

        layout_name = SLIDE_TYPE_TO_LAYOUT[slide_model.type]
        layout = inspection.get_layout(layout_name)
        pptx_slide = prs.slides.add_slide(layout)
        _rename_slide_placeholders(pptx_slide, slide_model.type)
        _copy_layout_lstStyles(pptx_slide, layout)

        renderer = SLIDE_RENDERERS[slide_model.type]
        renderer(slide_model, pptx_slide)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
