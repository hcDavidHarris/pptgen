"""Playbook execution engine — Phase 4 Stage 2.

Takes a *playbook_id* and *input_text*, loads routing metadata for the
playbook, extracts structured content from the text, and returns a
:class:`~pptgen.spec.presentation_spec.PresentationSpec`.

The extraction is entirely rule-based and deterministic.  Stage 3 will
extend this module to use the loaded :class:`RouteEntry` metadata
(``example_pattern``, ``output_yaml``, etc.) for slide planning.

Usage::

    from pptgen.playbook_engine.engine import execute_playbook

    spec = execute_playbook("meeting-notes-to-eos-rocks", notes_text)
"""

from __future__ import annotations

from pptgen.spec.presentation_spec import PresentationSpec

from .content_extractor import extract
from .playbook_loader import PlaybookNotFoundError, load_playbook


def execute_playbook(playbook_id: str, input_text: str) -> PresentationSpec:
    """Execute the playbook identified by *playbook_id* against *input_text*.

    Loads routing metadata for the playbook (for validation and future Stage 3
    use), then delegates content extraction to the rule-based extractor
    appropriate for the playbook.

    Args:
        playbook_id: Playbook identifier as returned by
                     :func:`~pptgen.input_router.route_input`, e.g.
                     ``"meeting-notes-to-eos-rocks"``.
        input_text:  Normalised text to extract content from.

    Returns:
        A valid :class:`~pptgen.spec.presentation_spec.PresentationSpec`
        populated from the extracted content.

    Raises:
        :class:`~pptgen.playbook_engine.playbook_loader.PlaybookNotFoundError`:
            If *playbook_id* is not in the routing table and is not the
            generic fallback identifier.
    """
    # Load routing metadata.  Raises PlaybookNotFoundError for genuinely
    # unknown IDs.  Returns None for the generic fallback (no table entry).
    # The route_entry is not consumed in Stage 2 but is loaded here to:
    #   a) validate the playbook_id early, and
    #   b) establish the seam for Stage 3 (which will use example_pattern).
    _route_entry = load_playbook(playbook_id)  # noqa: F841 — used in Stage 3

    return extract(playbook_id, input_text)
