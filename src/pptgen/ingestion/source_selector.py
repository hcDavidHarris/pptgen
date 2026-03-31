"""Source selector — maps source_type to an extractor callable.

Architectural role
------------------
Extractors sit below the adapter layer in the ingestion pipeline.
They receive a normalised SourceDocument (produced by an adapter) and
derive a list of ExtractedInsights from it.

They do NOT fetch or normalise sources — that is the adapter's job.

Phase 12A: returns stub extractors only.  Real extraction logic is
wired in Phase 12B/12C/12D alongside the corresponding adapter phases.

Usage:
    extractor = select_extractor("zoom_transcript")
    insights  = extractor(source_document)

Source-type registry
--------------------
"transcript"      — legacy direct-path entry (Phase 12A, kept for compat)
"zoom_transcript" — normalised path via TranscriptAdapter (Phase 12A.1+)
"ado_board"       — ADO board path (both direct and adapter-normalised)
"ado_repo"        — ADO repo path (both direct and adapter-normalised)
"""

from __future__ import annotations

from typing import Callable

from .extractors.ado_board_extractor import extract as _ado_board_extract
from .extractors.ado_repo_extractor import extract as _ado_repo_extract
from .extractors.transcript_extractor import extract as _transcript_extract
from .extractors.zoom_transcript_extractor import extract as _zoom_transcript_extract

# ---------------------------------------------------------------------------
# Registry: source_type -> extractor callable
# ---------------------------------------------------------------------------

_EXTRACTOR_REGISTRY: dict[str, Callable] = {
    # Legacy direct-path entry (Phase 12A) — kept for backwards compat; uses stub
    "transcript": _transcript_extract,
    # Adapter-normalised path (Phase 12B) — real rule-based extractor
    "zoom_transcript": _zoom_transcript_extract,
    "ado_board": _ado_board_extract,
    "ado_repo": _ado_repo_extract,
}


class UnknownSourceTypeError(ValueError):
    """Raised when no extractor is registered for the given source_type."""


def select_extractor(source_type: str) -> Callable:
    """Return the extractor callable registered for source_type.

    Args:
        source_type: The source type identifier (e.g. "transcript", "ado_board").

    Returns:
        A callable with signature ``(source_document: SourceDocument) -> list[ExtractedInsight]``.

    Raises:
        UnknownSourceTypeError: If source_type is not registered.
    """
    extractor = _EXTRACTOR_REGISTRY.get(source_type)
    if extractor is None:
        registered = sorted(_EXTRACTOR_REGISTRY.keys())
        raise UnknownSourceTypeError(
            f"No extractor registered for source_type={source_type!r}. "
            f"Registered types: {registered}"
        )
    return extractor


def registered_source_types() -> list[str]:
    """Return all currently registered source type identifiers."""
    return sorted(_EXTRACTOR_REGISTRY.keys())
