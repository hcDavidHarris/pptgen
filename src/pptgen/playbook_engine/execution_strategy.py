"""Execution strategy enum, constants, and dispatcher.

The playbook execution engine supports two strategies:

- ``"deterministic"`` — rule-based extraction, no external calls, current default.
- ``"ai"``            — mock AI execution path; real LLM integration in Phase 5B.

Prefer :class:`ExecutionMode` for type-safe usage.  Raw string values are
accepted everywhere for backwards compatibility with callers that predate the
enum.
"""

from __future__ import annotations

from enum import Enum

from ..spec.presentation_spec import PresentationSpec


class ExecutionMode(str, Enum):
    """Typed execution-mode values.

    Because :class:`ExecutionMode` inherits from ``str``, any
    ``ExecutionMode`` instance compares equal to the corresponding plain
    string (e.g. ``ExecutionMode.DETERMINISTIC == "deterministic"`` is
    ``True``) and can be used wherever a ``str`` is expected.
    """

    DETERMINISTIC = "deterministic"
    AI = "ai"


# Plain-string aliases kept for backward compatibility.
DETERMINISTIC: str = ExecutionMode.DETERMINISTIC.value
AI: str = ExecutionMode.AI.value

#: Set of all recognised strategy value strings.
VALID_STRATEGIES: frozenset[str] = frozenset(m.value for m in ExecutionMode)


class UnknownStrategyError(ValueError):
    """Raised when an unrecognised strategy name is supplied."""

    from pptgen.errors import ErrorCategory
    category = ErrorCategory.CONFIGURATION


def dispatch(
    playbook_id: str,
    input_text: str,
    strategy: str | ExecutionMode,
) -> PresentationSpec:
    """Route execution to the appropriate executor for *strategy*.

    Args:
        playbook_id: Playbook identifier (e.g. ``"meeting-notes-to-eos-rocks"``).
        input_text:  Normalised text to extract content from.
        strategy:    Execution strategy — ``"deterministic"`` / ``"ai"`` or the
                     corresponding :class:`ExecutionMode` member.

    Returns:
        A valid :class:`~pptgen.spec.presentation_spec.PresentationSpec`.

    Raises:
        UnknownStrategyError: If *strategy* is not in :data:`VALID_STRATEGIES`.
    """
    strategy_value = strategy.value if isinstance(strategy, ExecutionMode) else strategy

    if strategy_value not in VALID_STRATEGIES:
        raise UnknownStrategyError(
            f"Unknown execution strategy '{strategy_value}'.  "
            f"Valid strategies: {', '.join(sorted(VALID_STRATEGIES))}."
        )

    if strategy_value == DETERMINISTIC:
        from .deterministic_executor import run as _det_run
        return _det_run(playbook_id, input_text)

    # strategy_value == AI
    from .ai_executor import run as _ai_run
    return _ai_run(playbook_id, input_text)
