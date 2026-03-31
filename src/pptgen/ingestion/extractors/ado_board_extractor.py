"""Stub extractor for Azure DevOps board sources.

Phase 12A: returns a deterministic stub insight list.
Phase 12C: replace with real ADO board export extraction logic.
"""

from __future__ import annotations

from ..ingestion_models import ExtractedInsight, SourceDocument


def extract(source_document: SourceDocument) -> list[ExtractedInsight]:
    """Extract insights from an ADO board source.

    Args:
        source_document: A SourceDocument with source_type="ado_board".

    Returns:
        A list of ExtractedInsight stubs.
    """
    return [
        ExtractedInsight(
            category="delivery",
            text="Sprint delivery velocity and completion rate were captured.",
            confidence=0.85,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="aggregated",
            metadata={},
        ),
        ExtractedInsight(
            category="blocker",
            text="Outstanding work items represent active blockers to delivery.",
            confidence=0.8,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="inferred",
            metadata={},
        ),
        ExtractedInsight(
            category="metric",
            text="Cycle time and throughput metrics were extracted from the board.",
            confidence=0.9,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="aggregated",
            metadata={},
        ),
    ]
