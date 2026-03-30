"""Normalizer — Phase 11A / 11C.

Converts EnrichedSlideContent into a dict compatible with the existing
generation pipeline.  Does NOT modify the pipeline itself.

Phase 11C: ``_ci_metadata`` now includes ``primitive`` and
``primitive_validation`` when present.  The renderer ignores ``_ci_metadata``
entirely — this is purely for observability and downstream tooling.
"""

from __future__ import annotations

from .content_models import EnrichedSlideContent


def normalize_for_pipeline(content: EnrichedSlideContent) -> dict:
    """Convert EnrichedSlideContent to a pipeline-compatible dict.

    Maps enriched content fields to the keys expected by the existing
    deck definition structure (title, content, bullets, notes).

    The ``_ci_metadata`` key carries content intelligence provenance —
    including the semantic primitive assignment and validation result from
    Phase 11C — and is ignored by the renderer.

    Args:
        content: Fully enriched and critiqued slide content.

    Returns:
        dict compatible with the existing deck definition slide schema.
    """
    ci_metadata = dict(content.metadata)
    # Surface primitive at the top level of _ci_metadata for easy inspection.
    if content.primitive is not None:
        ci_metadata.setdefault("primitive", content.primitive)

    return {
        "title": content.title,
        "content": content.assertion or "",
        "bullets": list(content.supporting_points),
        "notes": "; ".join(content.implications) if content.implications else "",
        "_ci_metadata": ci_metadata,
    }
