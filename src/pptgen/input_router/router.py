"""Public interface for the pptgen input router.

The router is the single entry point for Stage 1 of the Phase 4 pipeline.
It accepts raw text input, normalises it, and returns exactly one playbook
identifier.

Example::

    from pptgen.input_router.router import route_input

    playbook_id = route_input(notes_text)
    # e.g. "meeting-notes-to-eos-rocks"
"""

from __future__ import annotations

from .classifier import FALLBACK_PLAYBOOK, classify


class InputRouterError(Exception):
    """Raised for invalid inputs that cannot be routed (e.g. non-string)."""


def route_input(input_text: str) -> str:
    """Route raw input text to exactly one playbook identifier.

    Args:
        input_text: Raw text to classify.  May be any string, including
                    empty.  Leading/trailing whitespace is stripped before
                    classification.

    Returns:
        A playbook identifier string, e.g. ``"meeting-notes-to-eos-rocks"``.
        Returns ``"generic-summary-playbook"`` for empty or unrecognised input.
        Always returns exactly one value.

    Raises:
        InputRouterError: If *input_text* is not a string (e.g. ``None``).
    """
    if not isinstance(input_text, str):
        raise InputRouterError(
            f"route_input() expects a str, got {type(input_text).__name__!r}."
        )

    normalised = input_text.strip().lower()

    if not normalised:
        return FALLBACK_PLAYBOOK

    return classify(normalised)
