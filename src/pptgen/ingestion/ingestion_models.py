"""Core data models for the ingestion framework.

Three root types flow through the pipeline:

    SourceDocument   — raw input from a connector (transcript, ADO, etc.)
    ExtractedInsight — a single atomic insight derived from a source
    BaseBrief        — the typed, structured output delivered to Content Intelligence

All three are plain dataclasses.  No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceDocument:
    """Raw source input entering the ingestion pipeline.

    Attributes:
        source_type:  Connector type identifier (e.g. "transcript", "ado_board").
        source_id:    Optional identifier for the originating resource.
        title:        Human-readable label for the document.
        content:      Raw text or serialised payload; may be None for metadata-only sources.
        metadata:     Arbitrary key-value bag for connector-specific data.
    """

    source_type: str
    source_id: str | None
    title: str
    content: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


VALID_DERIVATION_TYPES: frozenset[str] = frozenset(
    {"quoted", "summarized", "inferred", "aggregated"}
)


@dataclass
class ExtractedInsight:
    """A single atomic insight extracted from a SourceDocument.

    Attributes:
        category:        Semantic category (e.g. "theme", "risk", "metric", "action").
        text:            The insight text.
        confidence:      Extraction confidence in [0.0, 1.0]; None when not computable.
        source_type:     Mirrors SourceDocument.source_type for provenance tracing.
        source_id:       Mirrors SourceDocument.source_id for provenance tracing.
        source_pointer:  Optional fine-grained pointer (e.g. timestamp, line ref).
        derivation_type: How the insight was produced.
                         Must be one of: "quoted", "summarized", "inferred", "aggregated".
        metadata:        Arbitrary key-value bag for extractor-specific data.
    """

    category: str
    text: str
    confidence: float | None
    source_type: str
    source_id: str | None
    source_pointer: str | None
    derivation_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseBrief:
    """Typed, structured output delivered to Content Intelligence.

    Attributes:
        brief_type:  Taxonomy type (e.g. "strategic", "delivery", "architecture", "eos_rocks").
        topic:       Primary subject of the presentation.
        goal:        Intended outcome or purpose.
        audience:    Target audience description.
        sections:    Ordered list of section dicts; each has at minimum a "title" key.
        metadata:    Arbitrary key-value bag.
        provenance:  List of provenance record dicts (serialised BriefProvenance).
        confidence:  Aggregate confidence derived from source insights; None if unavailable.
    """

    brief_type: str
    topic: str
    goal: str
    audience: str
    sections: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: list[dict[str, Any]] = field(default_factory=list)
    confidence: float | None = None
