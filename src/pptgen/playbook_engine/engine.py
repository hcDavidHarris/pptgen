"""Playbook execution engine — Phase 5A.

Public API::

    # Existing backward-compatible entrypoint (returns PresentationSpec)
    spec = execute_playbook(playbook_id, input_text, strategy="deterministic")

    # Extended entrypoint that also returns a fallback note (used by pipeline)
    spec, notes = execute_playbook_full(playbook_id, input_text, strategy="ai")

Dispatches to the appropriate executor based on *strategy*:

- ``"deterministic"`` — rule-based extraction, no external calls (default).
- ``"ai"``            — AI-assisted generation; mock in Phase 5A, real LLM in 5B.

If the AI executor raises a controlled error, execution falls back to the
deterministic path and the fallback reason is returned in the *notes* string.
"""

from __future__ import annotations

from ..spec.presentation_spec import PresentationSpec
from .execution_strategy import (
    AI,
    DETERMINISTIC,
    UnknownStrategyError,
    dispatch,
)


def execute_playbook(
    playbook_id: str,
    input_text: str,
    strategy: str = DETERMINISTIC,
) -> PresentationSpec:
    """Execute the playbook, returning only the spec.

    Backward-compatible wrapper around :func:`execute_playbook_full`.
    Callers that do not need the fallback note (including all pre-Phase-5A
    code) should use this function.

    Args:
        playbook_id: Playbook identifier (e.g. ``"meeting-notes-to-eos-rocks"``).
        input_text:  Normalised text to process.
        strategy:    Execution strategy — ``"deterministic"`` (default) or
                     ``"ai"``.

    Returns:
        A valid :class:`~pptgen.spec.presentation_spec.PresentationSpec`.

    Raises:
        :class:`~pptgen.playbook_engine.execution_strategy.UnknownStrategyError`:
            If *strategy* is not a recognised value.
        :class:`~pptgen.playbook_engine.playbook_loader.PlaybookNotFoundError`:
            If *playbook_id* is unknown (deterministic path only).
    """
    spec, _ = execute_playbook_full(playbook_id, input_text, strategy)
    return spec


def execute_playbook_full(
    playbook_id: str,
    input_text: str,
    strategy: str = DETERMINISTIC,
) -> tuple[PresentationSpec, str]:
    """Execute the playbook, returning both the spec and an optional note.

    Use this function from the pipeline when you need to surface AI fallback
    information in :class:`~pptgen.pipeline.PipelineResult.notes`.

    Args:
        playbook_id: Playbook identifier.
        input_text:  Normalised text to process.
        strategy:    Execution strategy — ``"deterministic"`` or ``"ai"``.

    Returns:
        ``(spec, notes)`` — *notes* is an empty string on normal execution, or
        a human-readable fallback message when the AI executor fell back to
        deterministic.

    Raises:
        :class:`~pptgen.playbook_engine.execution_strategy.UnknownStrategyError`:
            If *strategy* is not a recognised value.
        :class:`~pptgen.playbook_engine.playbook_loader.PlaybookNotFoundError`:
            If *playbook_id* is unknown (deterministic path only).
    """
    if strategy not in (DETERMINISTIC, AI):
        raise UnknownStrategyError(
            f"Unknown execution strategy '{strategy}'.  "
            f"Valid strategies: ai, deterministic."
        )

    if strategy == AI:
        return _run_ai_with_fallback(playbook_id, input_text)

    spec = dispatch(playbook_id, input_text, DETERMINISTIC)
    return spec, ""


# ---------------------------------------------------------------------------
# AI execution with deterministic fallback
# ---------------------------------------------------------------------------

def _run_ai_with_fallback(
    playbook_id: str,
    input_text: str,
) -> tuple[PresentationSpec, str]:
    """Attempt AI execution; fall back to deterministic on controlled failures.

    A "controlled failure" is any exception raised *inside* the AI executor
    (e.g. a malformed mock response, a future API timeout).  Programming errors
    such as :class:`TypeError` still propagate.

    Returns:
        ``(spec, notes)`` — *notes* is empty on success, or contains a
        fallback reason on fallback.
    """
    try:
        spec = dispatch(playbook_id, input_text, AI)
        return spec, ""
    except (ValueError, KeyError, AttributeError) as exc:
        fallback_note = (
            f"AI executor failed ({type(exc).__name__}: {exc}); "
            f"fell back to deterministic."
        )
        spec = dispatch(playbook_id, input_text, DETERMINISTIC)
        return spec, fallback_note
