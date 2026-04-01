"""Deterministic playbook executor.

Wraps the existing rule-based content extraction pipeline.  This is the
canonical, stable execution path that has been in use since Phase 4 Stage 2.

Behavior is identical to the pre-Phase-5A ``execute_playbook()`` implementation:
1. Validate *playbook_id* via the routing table (raises
   :class:`PlaybookNotFoundError` for unknown IDs; returns ``None`` for the
   generic fallback, which is handled by the extractor).
2. Delegate to the appropriate rule-based extraction strategy.

No external calls.  Same input always produces same output.
"""

from __future__ import annotations

from ..spec.presentation_spec import PresentationSpec
from .content_extractor import extract
from .playbook_loader import load_playbook


def run(playbook_id: str, input_text: str) -> PresentationSpec:
    """Execute deterministic rule-based extraction for *playbook_id*.

    Args:
        playbook_id: Playbook identifier (e.g. ``"ado-summary-to-weekly-delivery"``).
        input_text:  Normalised text to extract content from.

    Returns:
        A valid :class:`~pptgen.spec.presentation_spec.PresentationSpec`.

    Raises:
        :class:`~pptgen.playbook_engine.playbook_loader.PlaybookNotFoundError`:
            If *playbook_id* is not in the routing table and is not the
            generic fallback.
    """
    load_playbook(playbook_id)  # validates ID; returns None for generic fallback
    return extract(playbook_id, input_text)
