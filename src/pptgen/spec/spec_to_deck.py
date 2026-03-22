"""Spec-to-deck translator.

Converts a PresentationSpec (semantic content) into a deck YAML structure
(a plain dict) that can be written to a .yaml file and processed by the
standard pptgen validate → build pipeline.

Translation rules
-----------------
1. A title slide is always emitted first, using spec.title and spec.subtitle.
2. Each SectionSpec produces:
   a. A ``section`` slide (if include_section_divider is True).
   b. A ``bullets`` slide if section.bullets is non-empty.
   c. One or more ``metric_summary`` slides if section.metrics is non-empty
      (split into groups of 4, the maximum per slide).
   d. One ``image_caption`` slide per entry in section.images.
3. Sections with no content (no bullets, metrics, or images) still emit the
   section divider (if enabled) so the deck has a placeholder structure.
4. The returned dict matches the pptgen deck YAML schema and can be passed
   directly to ``pptgen.loaders.yaml_loader.load_deck()`` via a YAML dump.
"""

from __future__ import annotations

from typing import Any

from .presentation_spec import PresentationSpec, SectionSpec


_MAX_METRICS_PER_SLIDE = 4
_MAX_BULLETS_PER_SLIDE = 6


def convert_spec_to_deck(spec: PresentationSpec) -> dict[str, Any]:
    """Convert *spec* to a deck YAML structure (plain dict).

    Args:
        spec: A validated PresentationSpec instance.

    Returns:
        A dict matching the pptgen deck YAML schema.  The dict can be
        serialised with ``yaml.dump()`` and loaded by ``load_deck()``.
    """
    slides: list[dict[str, Any]] = []

    # --- Title slide ---
    slides.append({
        "type": "title",
        "title": spec.title,
        "subtitle": spec.subtitle,
    })

    # --- Section slides ---
    for idx, section in enumerate(spec.sections, start=1):
        _translate_section(section, slides, section_idx=idx)

    return {
        "deck": {
            "title": spec.title,
            "template": spec.template,
            "author": spec.author,
            "version": "1.0",
        },
        "slides": slides,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _translate_section(
    section: SectionSpec,
    slides: list[dict[str, Any]],
    section_idx: int,
) -> None:
    """Append all slides generated from *section* to *slides*."""

    # Section divider
    if section.include_section_divider:
        slides.append({
            "type": "section",
            "id": f"section_{section_idx}",
            "section_title": section.title,
        })

    # Bullets (split into groups of _MAX_BULLETS_PER_SLIDE)
    if section.bullets:
        for chunk_idx, chunk in enumerate(
            _chunks(section.bullets, _MAX_BULLETS_PER_SLIDE), start=1
        ):
            slide: dict[str, Any] = {
                "type": "bullets",
                "id": f"bullets_{section_idx}_{chunk_idx}",
                "title": section.title,
                "bullets": chunk,
            }
            slides.append(slide)

    # Metrics (split into groups of _MAX_METRICS_PER_SLIDE)
    if section.metrics:
        for chunk_idx, chunk in enumerate(
            _chunks(section.metrics, _MAX_METRICS_PER_SLIDE), start=1
        ):
            metric_slide: dict[str, Any] = {
                "type": "metric_summary",
                "id": f"metrics_{section_idx}_{chunk_idx}",
                "title": section.title,
                "metrics": [_metric_to_dict(m) for m in chunk],
            }
            slides.append(metric_slide)

    # Images (one slide each)
    for img_idx, image in enumerate(section.images, start=1):
        slides.append({
            "type": "image_caption",
            "id": f"image_{section_idx}_{img_idx}",
            "title": image.title or section.title,
            "image_path": image.path,
            "caption": image.caption,
        })


def _metric_to_dict(metric) -> dict[str, Any]:
    d: dict[str, Any] = {"label": metric.label, "value": metric.value}
    if metric.unit is not None:
        d["unit"] = metric.unit
    return d


def _chunks(lst: list, size: int):
    """Yield successive fixed-size chunks from *lst*."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
