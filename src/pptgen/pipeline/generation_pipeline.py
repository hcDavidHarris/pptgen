"""Generation pipeline — Phase 4 orchestration seam.

This module is the stable boundary between raw input and the presentation
generation workflow.  Stage 1 is complete (routing); later stages will
extend :class:`PipelineResult` and fill the generation steps below.

Current pipeline::

    generate_presentation(input_text)
        │
        ├─ validate input type
        ├─ normalise (strip)
        ├─ route_input()  →  playbook_id
        └─ return PipelineResult(stage="routed", ...)

Future stages will add::

    PipelineResult.presentation_spec   (Stage 2 — playbook execution)
    PipelineResult.slide_plan          (Stage 3 — slide planner)
    PipelineResult.deck_definition     (Stage 4 — deck YAML)
    PipelineResult.output_path         (Stage 5 — renderer)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..input_router import InputRouterError, route_input


class PipelineError(Exception):
    """Raised for invalid inputs at the pipeline boundary."""


@dataclass
class PipelineResult:
    """Structured result returned by :func:`generate_presentation`.

    Attributes:
        stage:       Current pipeline stage.  ``"routed"`` after Stage 1.
        playbook_id: Playbook identifier selected by the input router.
        input_text:  The normalised input text that was processed.
        notes:       Optional diagnostic notes about the routing decision.
    """

    stage: str
    playbook_id: str
    input_text: str
    notes: str = field(default="")


def generate_presentation(input_text: str) -> PipelineResult:
    """Entry point for the presentation generation pipeline.

    Validates *input_text*, routes it to a playbook, and returns a
    :class:`PipelineResult` describing the routing outcome.

    Args:
        input_text: Raw text to process (meeting notes, sprint summary,
                    architecture notes, etc.).  May be any non-empty string.
                    Leading/trailing whitespace is stripped before routing.

    Returns:
        :class:`PipelineResult` with ``stage="routed"`` and the selected
        ``playbook_id``.  Unknown content routes to
        ``"generic-summary-playbook"`` rather than raising.

    Raises:
        PipelineError: If *input_text* is not a string.
    """
    if not isinstance(input_text, str):
        raise PipelineError(
            f"generate_presentation() expects a str, "
            f"got {type(input_text).__name__!r}."
        )

    normalised = input_text.strip()

    try:
        playbook_id = route_input(normalised)
    except InputRouterError as exc:
        # InputRouterError is only raised for non-string input, which we
        # guard above.  Re-raise as a PipelineError so callers see a
        # consistent exception type from this boundary.
        raise PipelineError(str(exc)) from exc

    notes = "no signals matched; routed to fallback" if not normalised else ""

    return PipelineResult(
        stage="routed",
        playbook_id=playbook_id,
        input_text=normalised,
        notes=notes,
    )
