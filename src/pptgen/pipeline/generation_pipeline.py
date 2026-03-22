"""Generation pipeline — Phase 4 orchestration seam.

Current pipeline (Stage 5 complete)::

    generate_presentation(input_text, output_path=None, template_id=None)
        │
        ├─ validate input type
        ├─ normalise (strip)
        ├─ [if template_id given] validate it against registry early
        ├─ route_input()              →  playbook_id
        ├─ execute_playbook()         →  PresentationSpec
        ├─ resolve template           →  override > playbook default > spec default
        ├─ validate resolved template against registry
        ├─ set spec.template          →  resolved template_id
        ├─ plan_slides()              →  SlidePlan
        ├─ convert_spec_to_deck()     →  deck_definition (dict)
        ├─ [if output_path given]
        │   └─ render()               →  .pptx file written
        └─ return PipelineResult(stage="rendered" | "deck_planned", ...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import PptgenError as _PptgenError
from ..input_router import InputRouterError, route_input
from ..loaders.yaml_loader import parse_deck
from ..playbook_engine import PlaybookNotFoundError, execute_playbook, get_default_template
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
        stage:             Current pipeline stage.  ``"deck_planned"`` or
                           ``"rendered"`` after a successful render.
        playbook_id:       Playbook identifier selected by the input router.
        input_text:        The normalised input text that was processed.
        template_id:       Template ID used for rendering, resolved from the
                           override / playbook default / spec default chain.
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
    template_id: str | None = field(default=None)
    presentation_spec: PresentationSpec | None = field(default=None)
    slide_plan: SlidePlan | None = field(default=None)
    deck_definition: dict[str, Any] | None = field(default=None)
    output_path: str | None = field(default=None)
    notes: str = field(default="")


def generate_presentation(
    input_text: str,
    output_path: Path | None = None,
    template_id: str | None = None,
) -> PipelineResult:
    """Entry point for the presentation generation pipeline.

    Validates *input_text*, routes it to a playbook, executes the playbook,
    resolves the template, plans the slide structure, converts the spec to a
    deck definition, and optionally renders a ``.pptx`` file.

    Template resolution precedence:

    1. *template_id* parameter (explicit override)
    2. Playbook-specific default from :func:`~pptgen.playbook_engine.get_default_template`
    3. ``PresentationSpec.template`` field default (``"ops_review_v1"``)

    Args:
        input_text:  Raw text to process.  Leading/trailing whitespace is stripped.
        output_path: If provided, the deck is rendered and saved here.  The
                     parent directory is created when necessary.
        template_id: Optional template override.  Must be a registered template
                     ID.  Raises :class:`PipelineError` if the ID is not in the
                     registry.

    Returns:
        :class:`PipelineResult` with ``stage="rendered"`` when *output_path*
        was provided and rendering succeeded; ``stage="deck_planned"`` otherwise.

    Raises:
        PipelineError: If *input_text* is not a string, *template_id* is not
                       registered, or any internal pipeline step fails.
    """
    if not isinstance(input_text, str):
        raise PipelineError(
            f"generate_presentation() expects a str, "
            f"got {type(input_text).__name__!r}."
        )

    normalised = input_text.strip()

    # Validate the explicit override early so the caller gets a fast, clear error
    if template_id is not None:
        _validate_template_id(template_id)

    try:
        playbook_id = route_input(normalised)
    except InputRouterError as exc:
        raise PipelineError(str(exc)) from exc

    try:
        spec = execute_playbook(playbook_id, normalised)
    except PlaybookNotFoundError as exc:
        raise PipelineError(str(exc)) from exc

    # Resolve template: override > playbook default > spec default
    resolved_template = _resolve_template(playbook_id, template_id, spec.template)

    # Apply resolved template to the spec
    spec = spec.model_copy(update={"template": resolved_template})

    slide_plan = plan_slides(spec, playbook_id=playbook_id)
    deck_definition = convert_spec_to_deck(spec)

    notes = "no signals matched; routed to fallback" if not normalised else ""

    if output_path is None:
        return PipelineResult(
            stage="deck_planned",
            playbook_id=playbook_id,
            input_text=normalised,
            template_id=resolved_template,
            presentation_spec=spec,
            slide_plan=slide_plan,
            deck_definition=deck_definition,
            notes=notes,
        )

    _render(deck_definition, resolved_template, Path(output_path))

    return PipelineResult(
        stage="rendered",
        playbook_id=playbook_id,
        input_text=normalised,
        template_id=resolved_template,
        presentation_spec=spec,
        slide_plan=slide_plan,
        deck_definition=deck_definition,
        output_path=str(output_path),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Template resolution helpers
# ---------------------------------------------------------------------------

def _resolve_template(
    playbook_id: str,
    override: str | None,
    spec_default: str,
) -> str:
    """Return the template ID to use, applying precedence rules.

    Precedence (highest to lowest):

    1. *override* — explicit caller-supplied template ID
    2. Playbook-specific default from :func:`~pptgen.playbook_engine.get_default_template`
    3. *spec_default* — the PresentationSpec's current ``template`` value

    Args:
        playbook_id:  Resolved playbook identifier.
        override:     Explicit template ID supplied by the caller, or ``None``.
        spec_default: Current ``PresentationSpec.template`` value.

    Returns:
        A template ID string (never empty).
    """
    if override is not None:
        return override
    playbook_default = get_default_template(playbook_id)
    # get_default_template always returns a non-empty string, but fall back
    # to spec_default to be defensive
    return playbook_default or spec_default


def _validate_template_id(template_id: str) -> None:
    """Raise :class:`PipelineError` if *template_id* is not in the registry.

    Args:
        template_id: Template ID to validate.

    Raises:
        PipelineError: If *template_id* is not registered.
    """
    try:
        registry = TemplateRegistry.from_file(_REGISTRY_PATH)
    except _PptgenError as exc:
        raise PipelineError(str(exc)) from exc

    if not registry.exists(template_id):
        registered = sorted(e.template_id for e in registry.all())
        raise PipelineError(
            f"Template '{template_id}' is not registered.  "
            f"Registered templates: {', '.join(registered)}."
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
