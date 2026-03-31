"""Stub extractor for Azure DevOps repository sources.

Phase 12A: returns a deterministic stub insight list.
Phase 12D: replace with real ADO repo / PR / commit extraction logic.
"""

from __future__ import annotations

from ..ingestion_models import ExtractedInsight, SourceDocument


def extract(source_document: SourceDocument) -> list[ExtractedInsight]:
    """Extract insights from an ADO repository source.

    Args:
        source_document: A SourceDocument with source_type="ado_repo".

    Returns:
        A list of ExtractedInsight stubs.
    """
    return [
        ExtractedInsight(
            category="architecture",
            text="Recent pull request activity reflects architectural changes in progress.",
            confidence=0.75,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="summarized",
            metadata={},
        ),
        ExtractedInsight(
            category="quality",
            text="Code review patterns indicate areas of technical debt accumulation.",
            confidence=0.7,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="inferred",
            metadata={},
        ),
        ExtractedInsight(
            category="theme",
            text="Commit message patterns reveal dominant engineering themes.",
            confidence=0.65,
            source_type=source_document.source_type,
            source_id=source_document.source_id,
            source_pointer=None,
            derivation_type="summarized",
            metadata={},
        ),
    ]
