"""Generation pipeline — Phase 4 orchestration seam.

Current pipeline (Stage 2 complete)::

    generate_presentation(input_text)
        │
        ├─ validate input type
        ├─ normalise (strip)
        ├─ route_input()          →  playbook_id
        ├─ execute_playbook()     →  PresentationSpec
        └─ return PipelineResult(stage="spec_generated", ...)

Planned future stages::

    PipelineResult.slide_plan      (Stage 3 — slide planner)
    PipelineResult.deck_definition (Stage 4 — deck YAML)
    PipelineResult.output_path     (Stage 5 — renderer)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..input_router import InputRouterError, route_input
from ..playbook_engine import PlaybookNotFoundError, execute_playbook
from ..spec.presentation_spec import PresentationSpec


class PipelineError(Exception):
    """Raised for invalid inputs at the pipeline boundary."""


@dataclass
class PipelineResult:
    """Structured result returned by :func:`generate_presentation`.

    Attributes:
        stage:             Current pipeline stage.  ``"spec_generated"`` after
                           Stage 2.
        playbook_id:       Playbook identifier selected by the input router.
        input_text:        The normalised input text that was processed.
        presentation_spec: Extracted :class:`~pptgen.spec.presentation_spec.PresentationSpec`,
                           populated after Stage 2.  ``None`` only if
                           execution failed (should not occur in normal flow).
        notes:             Optional diagnostic notes.
    """

    stage: str
    playbook_id: str
    input_text: str
    presentation_spec: PresentationSpec | None = field(default=None)
    notes: str = field(default="")


def generate_presentation(input_text: str) -> PipelineResult:
    """Entry point for the presentation generation pipeline.

    Validates *input_text*, routes it to a playbook, executes the playbook
    to produce a :class:`~pptgen.spec.presentation_spec.PresentationSpec`,
    and returns a :class:`PipelineResult`.

    Args:
        input_text: Raw text to process (meeting notes, sprint summary,
                    architecture notes, etc.).  May be any string, including
                    empty.  Leading/trailing whitespace is stripped before
                    processing.

    Returns:
        :class:`PipelineResult` with ``stage="spec_generated"`` and a
        populated ``presentation_spec``.  Unknown content routes to
        ``"generic-summary-playbook"`` and still produces a valid spec.

    Raises:
        PipelineError: If *input_text* is not a string, or if an internal
                       pipeline error cannot be recovered from.
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
        raise PipelineError(str(exc)) from exc

    try:
        spec = execute_playbook(playbook_id, normalised)
    except PlaybookNotFoundError as exc:
        raise PipelineError(str(exc)) from exc

    notes = "no signals matched; routed to fallback" if not normalised else ""

    return PipelineResult(
        stage="spec_generated",
        playbook_id=playbook_id,
        input_text=normalised,
        presentation_spec=spec,
        notes=notes,
    )
