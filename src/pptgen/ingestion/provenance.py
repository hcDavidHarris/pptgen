"""Provenance model for ingestion briefs.

BriefProvenance records where a brief came from: which sources were consulted,
how many insights were extracted, how confident the extraction was, and what
derivation methods were used.  It is constructed from a list of ExtractedInsights
via build_provenance().
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .ingestion_models import ExtractedInsight


@dataclass
class BriefProvenance:
    """Provenance record attached to a BaseBrief.

    Attributes:
        source_types:               Deduplicated list of source_type values from insights.
        source_ids:                 Deduplicated list of source_id values (may contain None).
        extraction_timestamp:       ISO-8601 UTC timestamp when provenance was built.
        insight_counts_by_category: Number of insights per semantic category.
        derivation_summary:         Count of insights per derivation_type.
        confidence_summary:         min/max/mean confidence across insights with a value.
    """

    source_types: list[str]
    source_ids: list[str | None]
    extraction_timestamp: str
    insight_counts_by_category: dict[str, int]
    derivation_summary: dict[str, int]
    confidence_summary: dict[str, float | None]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for BaseBrief.provenance."""
        return asdict(self)


def build_provenance(insights: list[ExtractedInsight]) -> BriefProvenance:
    """Construct a BriefProvenance from a list of ExtractedInsights.

    Args:
        insights: List of insights produced by an extractor.

    Returns:
        A BriefProvenance summarising the extraction.
    """
    source_types: list[str] = _dedupe_ordered(i.source_type for i in insights)
    source_ids: list[str | None] = _dedupe_ordered(i.source_id for i in insights)

    insight_counts: dict[str, int] = {}
    derivation_counts: dict[str, int] = {}
    confidence_values: list[float] = []

    for insight in insights:
        insight_counts[insight.category] = insight_counts.get(insight.category, 0) + 1
        derivation_counts[insight.derivation_type] = (
            derivation_counts.get(insight.derivation_type, 0) + 1
        )
        if insight.confidence is not None:
            confidence_values.append(insight.confidence)

    confidence_summary: dict[str, float | None]
    if confidence_values:
        confidence_summary = {
            "min": min(confidence_values),
            "max": max(confidence_values),
            "mean": sum(confidence_values) / len(confidence_values),
        }
    else:
        confidence_summary = {"min": None, "max": None, "mean": None}

    return BriefProvenance(
        source_types=source_types,
        source_ids=source_ids,
        extraction_timestamp=_utc_now_iso(),
        insight_counts_by_category=insight_counts,
        derivation_summary=derivation_counts,
        confidence_summary=confidence_summary,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dedupe_ordered(values) -> list:
    """Return deduplicated items preserving first-seen order."""
    seen: set = set()
    result = []
    for v in values:
        key = v  # None is hashable
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
