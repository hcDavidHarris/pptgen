"""Execution strategy constants and dispatcher.

The playbook execution engine supports two strategies:

- ``"deterministic"`` — rule-based extraction, no external calls, current default.
- ``"ai"``            — mock AI execution path; real LLM integration in Phase 5B.

All external callers should use the string constants defined here rather than
hard-coding strategy names, so that future name changes require a single edit.
"""

from __future__ import annotations

from ..spec.presentation_spec import PresentationSpec


DETERMINISTIC = "deterministic"
AI = "ai"

#: Set of all recognised strategy names.
VALID_STRATEGIES: frozenset[str] = frozenset({DETERMINISTIC, AI})


class UnknownStrategyError(ValueError):
    """Raised when an unrecognised strategy name is supplied."""


def dispatch(
    playbook_id: str,
    input_text: str,
    strategy: str,
) -> PresentationSpec:
    """Route execution to the appropriate executor for *strategy*.

    Args:
        playbook_id: Playbook identifier (e.g. ``"meeting-notes-to-eos-rocks"``).
        input_text:  Normalised text to extract content from.
        strategy:    Execution strategy — ``"deterministic"`` or ``"ai"``.

    Returns:
        A valid :class:`~pptgen.spec.presentation_spec.PresentationSpec`.

    Raises:
        UnknownStrategyError: If *strategy* is not in :data:`VALID_STRATEGIES`.
    """
    if strategy not in VALID_STRATEGIES:
        raise UnknownStrategyError(
            f"Unknown execution strategy '{strategy}'.  "
            f"Valid strategies: {', '.join(sorted(VALID_STRATEGIES))}."
        )

    if strategy == DETERMINISTIC:
        from .deterministic_executor import run as _det_run
        return _det_run(playbook_id, input_text)

    # strategy == AI
    from .ai_executor import run as _ai_run
    return _ai_run(playbook_id, input_text)
