"""Adapter contract for the ingestion framework.

An adapter owns exactly one responsibility:

    Accept a source-specific payload or reference
    → normalise it into a SourceDocument

No extraction logic belongs here.
No brief-building logic belongs here.

MCP seam
--------
Adapters are the architectural seam where MCP-backed source retrieval
will be introduced.  The current Phase 12A.1 implementations accept
manual payloads only.  In future phases (12B/12C/12D), individual
adapter implementations can be extended to call an MCP server
(e.g. a Zoom MCP tool or an ADO MCP tool) instead of—or in addition
to—accepting a manual payload.  The contract below stays stable;
only the adapter's internal retrieval strategy changes.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..ingestion_models import SourceDocument


@runtime_checkable
class SourceAdapter(Protocol):
    """Protocol defining the adapter contract.

    All concrete adapters must implement this interface.

    The ``load`` method is the only public entry point.  It accepts a
    source-specific payload dict and returns a normalised SourceDocument.

    Payload contents are adapter-specific; see each concrete adapter for
    the expected keys.

    MCP note: Future implementations may ignore or supplement the payload
    by fetching content from an MCP server.  Callers should not assume
    the payload is the sole source of data in later phases.
    """

    def load(self, payload: dict[str, Any]) -> SourceDocument:
        """Normalise a source payload into a SourceDocument.

        Args:
            payload: A dict of source-specific fields.  Required keys
                     are defined by each concrete adapter.

        Returns:
            A normalised SourceDocument ready for the extraction pipeline.

        Raises:
            AdapterPayloadError: If required fields are missing or invalid.
        """
        ...


class AdapterPayloadError(ValueError):
    """Raised when an adapter receives an invalid or incomplete payload."""
