"""Generation pipeline — Phase 4 orchestration seam.

Current pipeline (Stage 3 complete)::

    generate_presentation(input_text)
        │
        ├─ validate input type
        ├─ normalise (strip)
        ├─ route_input()          →  playbook_id
        ├─ execute_playbook()     →  PresentationSpec
        ├─ plan_slides()          →  SlidePlan
        ├─ convert_spec_to_deck() →  deck_definition (dict)
        └─ return PipelineResult(stage="deck_planned", ...)

Planned future stages::

    PipelineResult.output_path  (Stage 4 — renderer / CLI generate command)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..input_router import InputRouterError, route_input
from ..playbook_engine import PlaybookNotFoundError, execute_playbook
from ..planner import SlidePlan, plan_slides
from ..spec.presentation_spec import PresentationSpec
from ..spec.spec_to_deck import convert_spec_to_deck


class PipelineError(Exception):
    """Raised for invalid inputs at the pipeline boundary."""


@dataclass
class PipelineResult:
    """Structured result returned by :func:`generate_presentation`.

    Attributes:
        stage:             Current pipeline stage.  ``"deck_planned"`` after
                           Stage 3.
        playbook_id:       Playbook identifier selected by the input router.
        input_text:        The normalised input text that was processed.
        presentation_spec: Extracted :class:`~pptgen.spec.presentation_spec.PresentationSpec`,
                           populated after Stage 2.  ``None`` only if
                           execution failed (should not occur in normal flow).
        slide_plan:        :class:`~pptgen.planner.SlidePlan` produced by the
                           slide planning engine.  Populated after Stage 3.
        deck_definition:   Deck YAML structure (plain dict) produced by the
                           spec-to-deck translator.  Populated after Stage 3.
                           Can be serialised with ``yaml.dump()`` and loaded by
                           ``pptgen.loaders.yaml_loader.load_deck()``.
        notes:             Optional diagnostic notes.
    """

    stage: str
    playbook_id: str
    input_text: str
    presentation_spec: PresentationSpec | None = field(default=None)
    slide_plan: SlidePlan | None = field(default=None)
    deck_definition: dict[str, Any] | None = field(default=None)
    notes: str = field(default="")


def generate_presentation(input_text: str) -> PipelineResult:
    """Entry point for the presentation generation pipeline.

    Validates *input_text*, routes it to a playbook, executes the playbook
    to produce a :class:`~pptgen.spec.presentation_spec.PresentationSpec`,
    plans the slide structure, and converts the spec to a deck definition.

    Args:
        input_text: Raw text to process (meeting notes, sprint summary,
                    architecture notes, etc.).  May be any string, including
                    empty.  Leading/trailing whitespace is stripped before
                    processing.

    Returns:
        :class:`PipelineResult` with ``stage="deck_planned"``, a populated
        ``presentation_spec``, a ``slide_plan``, and a ``deck_definition``.
        Unknown content routes to ``"generic-summary-playbook"`` and still
        produces a valid plan and deck definition.

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

    slide_plan = plan_slides(spec, playbook_id=playbook_id)
    deck_definition = convert_spec_to_deck(spec)

    notes = "no signals matched; routed to fallback" if not normalised else ""

    return PipelineResult(
        stage="deck_planned",
        playbook_id=playbook_id,
        input_text=normalised,
        presentation_spec=spec,
        slide_plan=slide_plan,
        deck_definition=deck_definition,
        notes=notes,
    )
