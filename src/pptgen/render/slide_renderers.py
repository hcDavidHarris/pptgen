"""Slide renderers.

Each renderer handles one slide type.  Renderers are pure functions with the
signature:

    renderer(slide_model, pptx_slide) -> None

They write content into the named placeholder shapes on *pptx_slide* and
return nothing.  No font, colour, or sizing logic lives here — that is the
template's responsibility.

The SLIDE_RENDERERS registry maps slide type strings to renderer functions.
The deck renderer dispatches through this registry rather than using
if/elif chains, so new slide types can be added by registering a new
function without touching the orchestration layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..models.slides import (
    BulletsSlide,
    ImageCaptionSlide,
    MetricSummarySlide,
    SectionSlide,
    TitleSlide,
    TwoColumnSlide,
)
from .placeholder_mapper import find_placeholder, set_bullets, set_text


# ---------------------------------------------------------------------------
# Individual slide renderers
# ---------------------------------------------------------------------------

def render_title_slide(model: TitleSlide, slide) -> None:
    set_text(slide, "TITLE", model.title)
    set_text(slide, "SUBTITLE", model.subtitle)


def render_section_slide(model: SectionSlide, slide) -> None:
    set_text(slide, "SECTION_TITLE", model.section_title)
    # SECTION_SUBTITLE is optional in the schema; skip gracefully if absent
    subtitle_shape = find_placeholder(slide, "SECTION_SUBTITLE", required=False)
    if subtitle_shape is not None:
        subtitle_shape.text_frame.clear()
        subtitle_shape.text_frame.paragraphs[0].text = (
            model.section_subtitle or ""
        )


def render_bullets_slide(model: BulletsSlide, slide) -> None:
    set_text(slide, "TITLE", model.title)
    set_bullets(slide, "BULLETS", model.bullets)


def render_two_column_slide(model: TwoColumnSlide, slide) -> None:
    set_text(slide, "TITLE", model.title)
    set_bullets(slide, "LEFT_CONTENT", model.left_content)
    set_bullets(slide, "RIGHT_CONTENT", model.right_content)


def render_metric_summary_slide(model: MetricSummarySlide, slide) -> None:
    """Render a metric_summary slide using the Phase 1 placeholder contract.

    All 4 metric positions (1–4) are always written.  Positions with no
    corresponding metric in the model receive empty strings, which clears
    any pre-existing template text.

    Value composition: value + unit (direct concatenation, no separator).
    Authors include any desired space in the unit string (e.g. " ms").
    """
    set_text(slide, "TITLE", model.title)

    for position in range(1, 5):
        metric_index = position - 1
        if metric_index < len(model.metrics):
            metric = model.metrics[metric_index]
            label = metric.label
            value = metric.value + (metric.unit or "")
        else:
            label = ""
            value = ""

        set_text(slide, f"METRIC_{position}_LABEL", label)
        set_text(slide, f"METRIC_{position}_VALUE", value)


def render_image_caption_slide(model: ImageCaptionSlide, slide) -> None:
    set_text(slide, "TITLE", model.title)
    set_text(slide, "CAPTION", model.caption)
    image_shape = find_placeholder(slide, "IMAGE", required=False)
    if image_shape is not None:
        image_path = Path(model.image_path)
        if image_path.exists() and hasattr(image_shape, "insert_picture"):
            image_shape.insert_picture(str(image_path))


# ---------------------------------------------------------------------------
# Renderer registry
# ---------------------------------------------------------------------------

#: Maps slide type string → renderer function.
#: Add new slide types here without changing the deck renderer.
SLIDE_RENDERERS: dict[str, Callable] = {
    "title": render_title_slide,
    "section": render_section_slide,
    "bullets": render_bullets_slide,
    "two_column": render_two_column_slide,
    "metric_summary": render_metric_summary_slide,
    "image_caption": render_image_caption_slide,
}
