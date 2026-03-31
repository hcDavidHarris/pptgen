"""Phase 12A / 12A.1 / 12B — Source Ingestion Framework.

Ingestion flow
--------------
    Adapter (source access / normalisation)
        ↓
    SourceDocument
        ↓
    Extractor (insight derivation)
        ↓
    BriefBuilder (synthesis)
        ↓
    BaseBrief
        ↓   (Phase 12B CI bridge)
    ContentIntent  →  run_content_intelligence()

Entry points
------------
    run_ingestion(source_document)
        Core pipeline.  Accepts a pre-built SourceDocument.

    ingest_from_payload(source_type, payload)
        Adapter-layer entry point.  Normalises a raw dict payload via
        the appropriate SourceAdapter, then calls run_ingestion().

    ingest_transcript_to_brief(payload)         [Phase 12B]
        High-level helper: transcript payload → typed BaseBrief.

    ingest_transcript_to_content_intent(payload) [Phase 12B]
        High-level helper: transcript payload → ContentIntent for CI.
"""

from .adapters import (
    AdapterPayloadError,
    AdoBoardAdapter,
    AdoRepoAdapter,
    SourceAdapter,
    TranscriptAdapter,
    UnknownAdapterError,
    select_adapter,
)
from .ci_bridge import ContentIntent, brief_to_content_intent
from .ingestion_models import BaseBrief, ExtractedInsight, SourceDocument
from .ingestion_pipeline import ingest_from_payload, run_ingestion
from .provenance import BriefProvenance, build_provenance
from .transcript_orchestrator import (
    ingest_transcript_to_brief,
    ingest_transcript_to_content_intent,
)

__all__ = [
    # Models
    "SourceDocument",
    "ExtractedInsight",
    "BaseBrief",
    # Provenance
    "BriefProvenance",
    "build_provenance",
    # Pipeline entry points
    "run_ingestion",
    "ingest_from_payload",
    # Phase 12B transcript orchestration
    "ingest_transcript_to_brief",
    "ingest_transcript_to_content_intent",
    # Phase 12B CI bridge
    "ContentIntent",
    "brief_to_content_intent",
    # Adapter layer
    "SourceAdapter",
    "AdapterPayloadError",
    "UnknownAdapterError",
    "TranscriptAdapter",
    "AdoBoardAdapter",
    "AdoRepoAdapter",
    "select_adapter",
]
