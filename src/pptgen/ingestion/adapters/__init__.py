"""Adapter layer for the ingestion framework.

Architectural role
------------------
Adapters are the entry point for all external source access.
They own exactly one responsibility:

    Accept a source-specific payload or reference
    → normalise it into a SourceDocument

Nothing else belongs here.  Extraction, brief-building, and validation
are downstream concerns handled by extractors, brief_builder, and
validators respectively.

MCP seam
--------
This layer is where MCP-backed source retrieval will be wired in future
phases.  Each adapter class is the seam for one source type:

    TranscriptAdapter  — Phase 12B: Zoom MCP
    AdoBoardAdapter    — Phase 12C: ADO Boards MCP
    AdoRepoAdapter     — Phase 12D: ADO Repos MCP

Public API
----------
    select_adapter(source_type) -> SourceAdapter
    SourceAdapter               (Protocol)
    AdapterPayloadError         (raised on invalid payload)
    UnknownAdapterError         (raised on unknown source_type)
"""

from __future__ import annotations

from typing import Any

from .ado_board_adapter import AdoBoardAdapter
from .ado_repo_adapter import AdoRepoAdapter
from .base import AdapterPayloadError, SourceAdapter
from .transcript_adapter import TranscriptAdapter

__all__ = [
    "SourceAdapter",
    "AdapterPayloadError",
    "UnknownAdapterError",
    "TranscriptAdapter",
    "AdoBoardAdapter",
    "AdoRepoAdapter",
    "select_adapter",
]


class UnknownAdapterError(ValueError):
    """Raised when no adapter is registered for the requested source_type."""


# ---------------------------------------------------------------------------
# Adapter registry: source_type -> adapter class
# ---------------------------------------------------------------------------

_ADAPTER_REGISTRY: dict[str, type] = {
    "zoom_transcript": TranscriptAdapter,
    "ado_board": AdoBoardAdapter,
    "ado_repo": AdoRepoAdapter,
}


def select_adapter(source_type: str) -> SourceAdapter:
    """Return a fresh adapter instance for the given source_type.

    Args:
        source_type: Identifier for the source (e.g. "zoom_transcript").

    Returns:
        An instance of the appropriate SourceAdapter implementation.

    Raises:
        UnknownAdapterError: If source_type is not registered.
    """
    adapter_cls = _ADAPTER_REGISTRY.get(source_type)
    if adapter_cls is None:
        registered = sorted(_ADAPTER_REGISTRY.keys())
        raise UnknownAdapterError(
            f"No adapter registered for source_type={source_type!r}. "
            f"Registered types: {registered}"
        )
    return adapter_cls()


def registered_adapter_types() -> list[str]:
    """Return all currently registered adapter source type identifiers."""
    return sorted(_ADAPTER_REGISTRY.keys())
