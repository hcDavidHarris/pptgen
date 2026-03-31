"""Stub extractor for meeting transcript sources.

Phase 12A: returns a deterministic stub insight list.
Phase 12B: replace with real Zoom / Teams transcript extraction logic.
"""

from __future__ import annotations

from ..ingestion_models import ExtractedInsight, SourceDocument


def extract(source_document: SourceDocument) -> list[ExtractedInsight]:
    """Extract insights from a meeting transcript source.

    Args:
        source_document: A SourceDocument with source_type="transcript".

    Returns:
        A list of ExtractedInsight stubs.
    """
    return [
        ExtractedInsight(
            category="theme",
            text="Key strategic themes were discussed during the meeting.",
            confidence=0.8,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="summarized",
            metadata={},
        ),
        ExtractedInsight(
            category="action",
            text="Follow-up actions were identified and assigned to owners.",
            confidence=0.75,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="inferred",
            metadata={},
        ),
        ExtractedInsight(
            category="risk",
            text="Potential blockers were raised that require leadership attention.",
            confidence=0.7,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="inferred",
            metadata={},
        ),
    ]
