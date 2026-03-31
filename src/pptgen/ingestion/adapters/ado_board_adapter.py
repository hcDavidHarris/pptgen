"""Adapter for Azure DevOps board sources.

Responsibility: normalise an ADO board payload into a SourceDocument.

This adapter is the seam where ADO Boards MCP-backed retrieval will be
introduced in Phase 12C.  Currently it accepts a manual payload only.

MCP extension point (Phase 12C)
--------------------------------
Replace or supplement the ``load`` body to call an ADO MCP tool
(e.g. ``mcp.ado.get_board(project=payload["project"], iteration=...)``)
and fold the returned work-item data into the SourceDocument.
The method signature and return type are stable.

Expected payload keys
---------------------
Required:
    title (str)        — human-readable label for the board / sprint

Optional:
    source_id (str)    — board or iteration identifier
    content (str)      — pre-serialised board summary text
    metadata (dict)    — board-specific context (project, team, iteration,
                         work-item counts, velocity, etc.)
"""

from __future__ import annotations

from typing import Any

from ..ingestion_models import SourceDocument
from .base import AdapterPayloadError

SOURCE_TYPE = "ado_board"


class AdoBoardAdapter:
    """Normalises ADO board payloads into SourceDocument.

    Phase 12A.1: manual payload only.
    Phase 12C:   extend to call ADO Boards MCP tool for live retrieval.
    """

    def load(self, payload: dict[str, Any]) -> SourceDocument:
        """Normalise an ADO board payload into a SourceDocument.

        Args:
            payload: Must contain ``title``.  May contain ``source_id``,
                     ``content``, and ``metadata``.

        Returns:
            SourceDocument with source_type="ado_board".

        Raises:
            AdapterPayloadError: If ``title`` is missing or empty.
        """
        title = payload.get("title", "")
        if not title or not str(title).strip():
            raise AdapterPayloadError(
                "AdoBoardAdapter: payload must include a non-empty 'title'"
            )

        return SourceDocument(
            source_type=SOURCE_TYPE,
            source_id=payload.get("source_id"),
            title=str(title).strip(),
            content=payload.get("content"),
            metadata=dict(payload.get("metadata") or {}),
        )
