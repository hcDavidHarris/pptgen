"""Generation pipeline — Phase 4 orchestration seam.

Current pipeline (Stage 4 complete)::

    generate_presentation(input_text, output_path=None)
        │
        ├─ validate input type
        ├─ normalise (strip)
        ├─ route_input()          →  playbook_id
        ├─ execute_playbook()     →  PresentationSpec
        ├─ plan_slides()          →  SlidePlan
        ├─ convert_spec_to_deck() →  deck_definition (dict)
        ├─ [if output_path given]
        │   └─ render()           →  .pptx file written
        └─ return PipelineResult(stage="rendered" | "deck_planned", ...)

Planned future stages::

    Stage 5: multi-template rendering, template auto-selection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import PptgenError as _PptgenError
from ..input_router import InputRouterError, route_input
from ..loaders.yaml_loader import parse_deck
from ..playbook_engine import PlaybookNotFoundError, execute_playbook
from ..planner import SlidePlan, plan_slides
from ..registry.registry import TemplateRegistry
from ..render import render_deck
from ..spec.presentation_spec import PresentationSpec
from ..spec.spec_to_deck import convert_spec_to_deck


_REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "registry.yaml"


class PipelineError(Exception):
    """Raised for invalid inputs or rendering failures at the pipeline boundary."""


@dataclass
class PipelineResult:
    """Structured result returned by :func:`generate_presentation`.

    Attributes:
        stage:             Current pipeline stage.  ``"deck_planned"`` after
                           Stage 3; ``"rendered"`` after a successful render.
        playbook_id:       Playbook identifier selected by the input router.
        input_text:        The normalised input text that was processed.
        presentation_spec: Extracted :class:`~pptgen.spec.presentation_spec.PresentationSpec`.
        slide_plan:        :class:`~pptgen.planner.SlidePlan` from the planning engine.
        deck_definition:   Deck YAML structure (plain dict) from the translator.
        output_path:       Absolute path to the rendered ``.pptx`` file, or
                           ``None`` if rendering was not requested.
        notes:             Optional diagnostic notes.
    """

    stage: str
    playbook_id: str
    input_text: str
    presentation_spec: PresentationSpec | None = field(default=None)
    slide_plan: SlidePlan | None = field(default=None)
    deck_definition: dict[str, Any] | None = field(default=None)
    output_path: str | None = field(default=None)
    notes: str = field(default="")


def generate_presentation(
    input_text: str,
    output_path: Path | None = None,
) -> PipelineResult:
    """Entry point for the presentation generation pipeline.

    Validates *input_text*, routes it to a playbook, executes the playbook,
    plans the slide structure, converts the spec to a deck definition, and
    optionally renders a ``.pptx`` file when *output_path* is provided.

    Args:
        input_text:  Raw text to process.  Leading/trailing whitespace is
                     stripped.  May be empty — routes to the generic playbook.
        output_path: If provided, the deck is rendered and saved to this path.
                     The parent directory is created if it does not exist.
                     When ``None``, the pipeline stops at ``stage="deck_planned"``
                     and no file is written.

    Returns:
        :class:`PipelineResult`.  ``stage="rendered"`` when *output_path* was
        provided and rendering succeeded; ``stage="deck_planned"`` otherwise.

    Raises:
        PipelineError: If *input_text* is not a string, or if an internal
                       pipeline step fails unrecoverably.
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

    if output_path is None:
        return PipelineResult(
            stage="deck_planned",
            playbook_id=playbook_id,
            input_text=normalised,
            presentation_spec=spec,
            slide_plan=slide_plan,
            deck_definition=deck_definition,
            notes=notes,
        )

    _render(deck_definition, spec.template, Path(output_path))

    return PipelineResult(
        stage="rendered",
        playbook_id=playbook_id,
        input_text=normalised,
        presentation_spec=spec,
        slide_plan=slide_plan,
        deck_definition=deck_definition,
        output_path=str(output_path),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Internal rendering helper
# ---------------------------------------------------------------------------

def _render(
    deck_definition: dict[str, Any],
    spec_template: str,
    output_path: Path,
) -> None:
    """Load *deck_definition*, resolve template, and write a ``.pptx`` to *output_path*.

    Args:
        deck_definition: Plain dict produced by :func:`~pptgen.spec.spec_to_deck.convert_spec_to_deck`.
        spec_template:   Template ID string from the PresentationSpec.
        output_path:     Destination path for the rendered ``.pptx`` file.

    Raises:
        PipelineError: Wraps any :class:`~pptgen.errors.PptgenError` raised by
                       the loader, registry, or renderer.
    """
    try:
        deck = parse_deck(deck_definition)
        registry = TemplateRegistry.from_file(_REGISTRY_PATH)
        entry = registry.get(spec_template)
        template_path = _REGISTRY_PATH.parent.parent / entry.path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_deck(deck, template_path, output_path)
    except _PptgenError as exc:
        raise PipelineError(str(exc)) from exc
