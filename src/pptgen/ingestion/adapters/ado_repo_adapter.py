"""Adapter for Azure DevOps repository sources.

Responsibility: normalise an ADO repository payload into a SourceDocument.

This adapter is the seam where ADO Repos MCP-backed retrieval will be
introduced in Phase 12D.  Currently it accepts a manual payload only.

MCP extension point (Phase 12D)
--------------------------------
Replace or supplement the ``load`` body to call an ADO MCP tool
(e.g. ``mcp.ado.get_repo_summary(org=..., repo=payload["source_id"])``)
and fold the returned PR / commit / README data into the SourceDocument.
The method signature and return type are stable.

Expected payload keys
---------------------
Required:
    title (str)        — human-readable label for the repository

Optional:
    source_id (str)    — repository identifier or URL slug
    content (str)      — pre-serialised content (README, architecture notes,
                         PR summary, etc.)
    metadata (dict)    — repo-specific context (language, PR count, recent
                         commit themes, branch strategy, etc.)
"""

from __future__ import annotations

from typing import Any

from ..ingestion_models import SourceDocument
from .base import AdapterPayloadError

SOURCE_TYPE = "ado_repo"


class AdoRepoAdapter:
    """Normalises ADO repository payloads into SourceDocument.

    Phase 12A.1: manual payload only.
    Phase 12D:   extend to call ADO Repos MCP tool for live retrieval.
    """

    def load(self, payload: dict[str, Any]) -> SourceDocument:
        """Normalise an ADO repository payload into a SourceDocument.

        Args:
            payload: Must contain ``title``.  May contain ``source_id``,
                     ``content``, and ``metadata``.

        Returns:
            SourceDocument with source_type="ado_repo".

        Raises:
            AdapterPayloadError: If ``title`` is missing or empty.
        """
        title = payload.get("title", "")
        if not title or not str(title).strip():
            raise AdapterPayloadError(
                "AdoRepoAdapter: payload must include a non-empty 'title'"
            )

        return SourceDocument(
            source_type=SOURCE_TYPE,
            source_id=payload.get("source_id"),
            title=str(title).strip(),
            content=payload.get("content"),
            metadata=dict(payload.get("metadata") or {}),
        )
