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

from pathlib import Path

from ..models.deck import DeckFile
from .slide_renderers import SLIDE_RENDERERS
from .template_inspector import inspect_template
from .template_loader import load_template


#: Maps slide type string → canonical layout name in the template.
#: This is the only place where slide types are coupled to layout names.
SLIDE_TYPE_TO_LAYOUT: dict[str, str] = {
    "title": "Title Layout",
    "section": "Section Layout",
    "bullets": "Bullets Layout",
    "two_column": "Two Column Layout",
    "metric_summary": "Metric Summary Layout",
    "image_caption": "Image Caption Layout",
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


def _rename_slide_placeholders(slide, slide_type: str) -> None:
    """Rename cloned placeholder shapes to their canonical pptgen names."""
    ph_names = _SLIDE_TYPE_PH_NAMES.get(slide_type, {})
    for shape in slide.shapes:
        pf = getattr(shape, "placeholder_format", None)
        if pf is not None and pf.idx in ph_names:
            shape.name = ph_names[pf.idx]


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

        renderer = SLIDE_RENDERERS[slide_model.type]
        renderer(slide_model, pptx_slide)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
