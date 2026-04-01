"""Adapter for Azure DevOps board sources.

Responsibility: normalise an ADO board payload into a SourceDocument.

This adapter is the seam where ADO Boards MCP-backed retrieval will be
introduced in a future phase.  Currently it accepts a manual/JSON payload.

MCP extension point (future)
-----------------------------
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
    metadata (dict)    — board-specific context; recognised keys:
                            work_items (list[dict])  — work item records
                            iteration  (str)         — sprint / iteration label
                            team       (str)         — team name
                            date       (str)         — reporting date (ISO-8601)

Work item field contract
------------------------
Each item in ``work_items`` may have any combination of the following keys
(all optional except ``title``):

    id           (int | str)   — work item identifier
    title        (str)         — work item title
    state        (str)         — e.g. "Active", "In Progress", "Blocked", "Done"
    type         (str)         — e.g. "Feature", "Bug", "Task", "Epic"
    work_item_type (str)       — alias for ``type`` (snake_case export)
    workItemType (str)         — alias for ``type`` (camelCase ADO REST API)
    owner        (str)         — assignee display name
    assigned_to  (str)         — alias for ``owner`` (snake_case export)
    assignedTo   (str)         — alias for ``owner`` (camelCase ADO REST API)
    priority     (int)         — 1=critical, 2=high, 3=medium, 4=low
    tags         (list[str])   — free-form classification tags
    created_date (str)         — ISO-8601 creation date
    updated_date (str)         — ISO-8601 last-update date

Unknown extra keys are preserved in the normalised item's ``extra`` field.
"""

from __future__ import annotations

from typing import Any

from ..ingestion_models import SourceDocument
from .base import AdapterPayloadError

SOURCE_TYPE = "ado_board"

# Hard ceiling on normalised work items to guard against oversized payloads.
_MAX_WORK_ITEMS = 200

# Fields that are lifted into the normalised item dict.
# Includes both snake_case and camelCase ADO API variants.
_KNOWN_ITEM_KEYS = frozenset(
    {
        "id", "title", "state",
        "type", "work_item_type", "workItemType",
        "owner", "assigned_to", "assignedTo",
        "priority", "tags",
        "created_date", "updated_date",
    }
)


class AdoBoardAdapter:
    """Normalises ADO board payloads into SourceDocument.

    Phase 12A.1: manual payload, no work_items processing.
    Phase 12C:   normalises work_items from metadata into a stable schema.
    """

    def load(self, payload: dict[str, Any]) -> SourceDocument:
        """Normalise an ADO board payload into a SourceDocument.

        Args:
            payload: Must contain ``title``.  May contain ``source_id``,
                     ``content``, and ``metadata``.  ``metadata.work_items``
                     is normalised into a stable internal representation and
                     stored back into the returned document's metadata.

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

        raw_meta: dict[str, Any] = dict(payload.get("metadata") or {})
        raw_items: list[Any] = raw_meta.get("work_items") or []

        # Guard against oversized payloads — silently cap at _MAX_WORK_ITEMS.
        if len(raw_items) > _MAX_WORK_ITEMS:
            raw_items = raw_items[:_MAX_WORK_ITEMS]

        # Normalise each work item into the stable internal schema.
        normalised_items = [
            _normalise_work_item(item)
            for item in raw_items
            if isinstance(item, dict)
        ]

        # Rebuild metadata with normalised work_items (preserving other keys).
        metadata: dict[str, Any] = {
            k: v for k, v in raw_meta.items() if k != "work_items"
        }
        metadata["work_items"] = normalised_items

        return SourceDocument(
            source_type=SOURCE_TYPE,
            source_id=payload.get("source_id"),
            title=str(title).strip(),
            content=payload.get("content"),
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Work item normalisation helper
# ---------------------------------------------------------------------------


def _normalise_work_item(item: dict[str, Any]) -> dict[str, Any]:
    """Coerce a raw work item dict into a stable internal representation.

    Handles common field name variations (``work_item_type`` vs ``type``,
    ``assigned_to`` vs ``owner``) and preserves unknown extra keys.

    Args:
        item: Raw work item dict from the incoming payload.

    Returns:
        Normalised dict with stable keys and typed values.
    """
    item_id = item.get("id")
    item_title = str(item.get("title", "")).strip()
    state = str(item.get("state", "")).strip()

    # Resolve ``type``: prefer explicit "type", then snake_case, then camelCase aliases.
    item_type = str(
        item.get("type") or item.get("work_item_type") or item.get("workItemType") or ""
    ).strip()

    # Resolve ``owner``: prefer explicit "owner", then snake_case, then camelCase aliases.
    owner_raw = item.get("owner") or item.get("assigned_to") or item.get("assignedTo")
    owner = str(owner_raw).strip() if owner_raw is not None else None

    # Priority: coerce to int where possible.
    priority_raw = item.get("priority")
    try:
        priority: int | None = int(priority_raw) if priority_raw is not None else None
    except (TypeError, ValueError):
        priority = None

    # Tags: accept list or comma-separated string.
    tags_raw = item.get("tags")
    if isinstance(tags_raw, list):
        tags = [str(t).strip() for t in tags_raw if str(t).strip()]
    elif isinstance(tags_raw, str) and tags_raw.strip():
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    else:
        tags = []

    created_date = item.get("created_date")
    updated_date = item.get("updated_date")

    # Collect extra keys not part of the known contract.
    extra = {k: v for k, v in item.items() if k not in _KNOWN_ITEM_KEYS}

    normalised: dict[str, Any] = {
        "id": item_id,
        "title": item_title,
        "state": state,
        "type": item_type,
        "owner": owner,
        "priority": priority,
        "tags": tags,
        "created_date": created_date,
        "updated_date": updated_date,
    }
    if extra:
        normalised["extra"] = extra

    return normalised
