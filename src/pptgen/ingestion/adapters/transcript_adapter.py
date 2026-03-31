"""Adapter for meeting transcript sources.

Responsibility: normalise a transcript payload into a SourceDocument.

This adapter is the seam where Zoom MCP-backed retrieval will be
introduced in a future phase.  Currently it accepts a manual payload only.

MCP extension point (future)
-----------------------------
Replace or supplement the ``load`` body to call a Zoom MCP tool
(e.g. ``mcp.zoom.get_transcript(meeting_id=payload["source_id"])``)
and fold the returned content into the SourceDocument.  The method
signature and return type are stable.

Expected payload keys
---------------------
Required:
    title (str)        — human-readable label for the meeting/transcript
    content (str)      — raw transcript text (non-empty)

Optional:
    source_id (str)    — meeting or recording identifier
    metadata (dict)    — arbitrary context (meeting date, participants,
                         meeting_type, speaker_map, tags, etc.)

Supported metadata fields
--------------------------
    meeting_date (str)       — ISO-8601 date of the meeting
    participants (list[str]) — list of participant names
    meeting_type (str)       — "eos", "l10", "rocks", or any label;
                               used by brief type selection
    speaker_map (dict)       — maps speaker token → display name
    tags (list[str])         — free-form classification tags
"""

from __future__ import annotations

from typing import Any

from ..ingestion_models import SourceDocument
from .base import AdapterPayloadError

SOURCE_TYPE = "zoom_transcript"


class TranscriptAdapter:
    """Normalises transcript payloads into SourceDocument.

    Phase 12A.1: manual payload only.
    Phase 12B:   requires non-empty content; preserves rich metadata.
    """

    def load(self, payload: dict[str, Any]) -> SourceDocument:
        """Normalise a transcript payload into a SourceDocument.

        Args:
            payload: Must contain ``title`` and ``content``.  May contain
                     ``source_id`` and ``metadata``.

        Returns:
            SourceDocument with source_type="zoom_transcript".

        Raises:
            AdapterPayloadError: If ``title`` or ``content`` is missing or empty.
        """
        title = payload.get("title", "")
        if not title or not str(title).strip():
            raise AdapterPayloadError(
                "TranscriptAdapter: payload must include a non-empty 'title'"
            )

        content = payload.get("content", "")
        if not content or not str(content).strip():
            raise AdapterPayloadError(
                "TranscriptAdapter: payload must include a non-empty 'content' "
                "(raw transcript text)"
            )

        return SourceDocument(
            source_type=SOURCE_TYPE,
            source_id=payload.get("source_id"),
            title=str(title).strip(),
            content=str(content).strip(),
            metadata=dict(payload.get("metadata") or {}),
        )
