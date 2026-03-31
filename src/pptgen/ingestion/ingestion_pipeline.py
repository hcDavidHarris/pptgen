"""Ingestion pipeline — orchestrates source → brief transformation.

Architectural boundaries
------------------------
Adapters   — source access / normalisation → SourceDocument
             (entry point: ingest_from_payload)
Extractors — SourceDocument → list[ExtractedInsight]
             (dispatched by select_extractor via source_type)
BriefBuilder — insights → typed BaseBrief
             (build_brief)

The two public entry points are:

    run_ingestion(source_document)
        For callers that already hold a SourceDocument (e.g. direct
        construction or earlier pipeline stages).

    ingest_from_payload(source_type, payload)
        For callers that hold a raw payload dict.  Selects the correct
        adapter, normalises the payload into a SourceDocument, then
        calls run_ingestion().

Pipeline stages (run_ingestion)
--------------------------------
    1. validate_source   — reject malformed SourceDocuments early
    2. select_extractor  — choose the right extractor for the source_type
    3. run extractor     — produce list[ExtractedInsight]
    4. build_brief       — assemble typed BaseBrief from document + insights
    5. validate_brief    — confirm the brief is structurally sound
    6. return brief

No external dependencies.  No LLM calls.  Fully deterministic.
"""

from __future__ import annotations

from typing import Any

from .adapters import select_adapter
from .brief_builder import build_brief
from .ingestion_models import BaseBrief, SourceDocument
from .source_selector import select_extractor
from .validators.brief_validator import validate_brief
from .validators.source_payload_validator import validate_source


class IngestionPipelineError(RuntimeError):
    """Raised when the ingestion pipeline encounters an unrecoverable error."""


def run_ingestion(source_document: SourceDocument) -> BaseBrief:
    """Run the full ingestion pipeline for a single SourceDocument.

    This is the core pipeline entry point.  Callers that hold a raw
    payload dict should use ``ingest_from_payload`` instead.

    Args:
        source_document: The normalised source document to ingest.

    Returns:
        A validated, typed BaseBrief ready for downstream consumption.

    Raises:
        SourceValidationError:  If the source document is malformed.
        UnknownSourceTypeError: If no extractor is registered for the source_type.
        BriefValidationError:   If the produced brief fails validation.
        IngestionPipelineError: For unexpected pipeline failures.
    """
    # Stage 1 — validate source
    validate_source(source_document)

    # Stage 2 — select extractor
    extractor = select_extractor(source_document.source_type)

    # Stage 3 — run extractor
    insights = extractor(source_document)

    # Stage 4 — build brief
    brief = build_brief(source_document, insights)

    # Stage 5 — validate brief
    validate_brief(brief)

    # Stage 6 — return
    return brief


def ingest_from_payload(source_type: str, payload: dict[str, Any]) -> BaseBrief:
    """Normalise a raw payload and run the full ingestion pipeline.

    This is the adapter-layer entry point.  It selects the correct
    adapter for the given source_type, normalises the payload into a
    SourceDocument, then delegates to run_ingestion().

    Args:
        source_type: Source identifier (e.g. "zoom_transcript", "ado_board").
        payload:     Source-specific dict; required keys depend on adapter.

    Returns:
        A validated, typed BaseBrief ready for downstream consumption.

    Raises:
        UnknownAdapterError:    If source_type has no registered adapter.
        AdapterPayloadError:    If the payload is missing required fields.
        SourceValidationError:  If the normalised SourceDocument is malformed.
        UnknownSourceTypeError: If no extractor is registered for the source_type.
        BriefValidationError:   If the produced brief fails validation.
    """
    adapter = select_adapter(source_type)
    source_document = adapter.load(payload)
    return run_ingestion(source_document)
