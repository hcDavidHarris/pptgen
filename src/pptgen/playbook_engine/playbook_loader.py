"""Playbook loader.

Resolves a playbook identifier to its routing metadata by consulting the
existing routing table.  Keeps routing-table parsing (already in
:mod:`pptgen.input_router.routing_table_loader`) separate from execution
logic in :mod:`pptgen.playbook_engine.engine`.

The ``generic-summary-playbook`` identifier is the router's fallback value
and intentionally absent from the routing table.  :func:`load_playbook`
returns ``None`` for it rather than raising, so the engine can apply the
generic extraction strategy without error.

Usage::

    from pptgen.playbook_engine.playbook_loader import load_playbook

    entry = load_playbook("meeting-notes-to-eos-rocks")
    # entry.playbook_path  → "docs/ai-playbooks/meeting-notes-to-eos-rocks.md"
    # entry.example_pattern → "examples/eos/eos_rocks.yaml"
"""

from __future__ import annotations

from pptgen.input_router.classifier import FALLBACK_PLAYBOOK
from pptgen.input_router.routing_table_loader import RouteEntry, load_routing_table


class PlaybookNotFoundError(Exception):
    """Raised when a playbook_id is not found in the routing table and is
    not the generic fallback."""


def load_playbook(playbook_id: str) -> RouteEntry | None:
    """Resolve *playbook_id* to its routing table entry.

    Args:
        playbook_id: Hyphen-separated playbook identifier as returned by
                     :func:`pptgen.input_router.route_input`, e.g.
                     ``"meeting-notes-to-eos-rocks"``.

    Returns:
        The matching :class:`~pptgen.input_router.routing_table_loader.RouteEntry`,
        or ``None`` if *playbook_id* is the generic fallback
        (``"generic-summary-playbook"``), which has no routing table entry.

    Raises:
        :class:`PlaybookNotFoundError`: If *playbook_id* is neither found in
            the routing table nor the generic fallback identifier.
    """
    if playbook_id == FALLBACK_PLAYBOOK:
        return None

    for entry in load_routing_table():
        if entry.playbook_id == playbook_id:
            return entry

    raise PlaybookNotFoundError(
        f"Playbook '{playbook_id}' not found in the routing table. "
        f"Check docs/ai-playbooks/routing_table.yaml or use "
        f"'{FALLBACK_PLAYBOOK}' for generic content."
    )
