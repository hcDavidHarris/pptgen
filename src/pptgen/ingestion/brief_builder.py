"""Brief builder — assembles a typed BaseBrief from a SourceDocument and insights.

Steps:
    1. Determine brief_type from source_type via brief_types.get_brief_factory().
    2. Group insights by category into sections.
    3. Compute aggregate confidence.
    4. Build BriefProvenance and attach as provenance list.
    5. Return a typed BaseBrief via the appropriate factory function.

Behaviour is deterministic: same inputs produce the same output.
"""

from __future__ import annotations

from typing import Any

from .brief_types import get_brief_factory, select_zoom_transcript_brief_factory
from .ingestion_models import BaseBrief, ExtractedInsight, SourceDocument
from .provenance import build_provenance

_ZOOM_SOURCE_TYPE = "zoom_transcript"


def build_brief(
    source_document: SourceDocument,
    insights: list[ExtractedInsight],
) -> BaseBrief:
    """Assemble a typed BaseBrief from a SourceDocument and its extracted insights.

    For zoom_transcript sources the brief type is determined dynamically via
    ``select_zoom_transcript_brief_factory`` (metadata flag + insight signals).
    All other source types use the static dispatch table.

    Args:
        source_document: The originating source document.
        insights:        Insights produced by the extractor for this document.

    Returns:
        A populated BaseBrief of the appropriate type.
    """
    if source_document.source_type == _ZOOM_SOURCE_TYPE:
        factory = select_zoom_transcript_brief_factory(
            source_document.metadata, insights
        )
    else:
        factory = get_brief_factory(source_document.source_type)

    sections = _build_sections(insights)
    provenance = build_provenance(insights)
    confidence = _aggregate_confidence(insights)

    brief = factory(
        topic=source_document.title,
        sections=sections,
        provenance=[provenance.to_dict()],
        confidence=confidence,
        metadata={"source_type": source_document.source_type},
    )
    return brief


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_sections(insights: list[ExtractedInsight]) -> list[dict[str, Any]]:
    """Group insights by category into ordered section dicts.

    Each section has:
        title:    The category name (title-cased).
        insights: List of insight text strings in insertion order.
    """
    grouped: dict[str, list[str]] = {}
    for insight in insights:
        grouped.setdefault(insight.category, []).append(insight.text)

    return [
        {"title": category.replace("_", " ").title(), "insights": texts}
        for category, texts in grouped.items()
    ]


def _aggregate_confidence(insights: list[ExtractedInsight]) -> float | None:
    """Compute the mean confidence across all insights that have a value."""
    values = [i.confidence for i in insights if i.confidence is not None]
    if not values:
        return None
    return sum(values) / len(values)
