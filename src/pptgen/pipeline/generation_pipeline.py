"""Generation pipeline — Phase 5A orchestration seam.

Current pipeline::

    generate_presentation(input_text, output_path=None, template_id=None, mode="deterministic",
                          theme_id=None)
        │
        ├─ validate input type and mode
        ├─ normalise (strip)
        ├─ [if template_id given] validate it against registry early
        ├─ route_input()                 →  playbook_id
        ├─ execute_playbook_full()       →  PresentationSpec + fallback note
        ├─ resolve template              →  override > playbook default > spec default
        ├─ set spec.template             →  resolved template_id
        ├─ plan_slides()                 →  SlidePlan
        ├─ convert_spec_to_deck()        →  deck_definition (dict)
        ├─ [if deck declares primitive]
        │   └─ resolve primitive         →  ResolvedSlidePrimitive
        │       injects layout + slots   →  deck_definition updated
        ├─ [if deck declares layout]
        │   └─ resolve layout            →  ResolvedLayout (validates slots)
        ├─ [if theme resolved]
        │   ├─ resolve design tokens     →  ResolvedStyleMap
        │   └─ substitute token refs     →  deck_definition (token refs replaced)
        ├─ resolve asset references      →  deck_definition (asset refs replaced)
        │                                   resolved_assets list populated
        ├─ [if output_path given]
        │   └─ render()                  →  .pptx file written
        └─ return PipelineResult(stage="rendered" | "deck_planned", ...)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..artifacts import write_artifacts
from ..config import get_settings
from ..design_system import (
    AssetResolver,
    DesignSystemRegistry,
    LayoutResolver,
    PrimitiveResolver,
    ResolvedAsset,
    ResolvedLayout,
    ResolvedSlidePrimitive,
    ResolvedStyleMap,
    TokenResolver,
)
from ..design_system.exceptions import DesignSystemError
from ..errors import InputSizeError, PptgenError as _PptgenError
from ..input_router import InputRouterError, route_input
from ..loaders.yaml_loader import parse_deck
from ..playbook_engine import PlaybookNotFoundError, execute_playbook_full, get_default_template
from ..playbook_engine.execution_strategy import DETERMINISTIC, VALID_STRATEGIES, ExecutionMode, UnknownStrategyError
from ..planner import SlidePlan, plan_slides
from ..registry.registry import TemplateRegistry
from ..render import render_deck
from ..runtime.run_context import RunContext
from ..spec.presentation_spec import PresentationSpec
from ..spec.spec_to_deck import convert_spec_to_deck


_REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "registry.yaml"


class PipelineError(Exception):
    """Raised for invalid inputs or rendering failures at the pipeline boundary."""

    from pptgen.errors import ErrorCategory
    category = ErrorCategory.SYSTEM


@dataclass
class PipelineResult:
    """Structured result returned by :func:`generate_presentation`.

    Attributes:
        stage:             Current pipeline stage (``"deck_planned"`` or ``"rendered"``).
        playbook_id:       Playbook identifier selected by the input router.
        input_text:        The normalised input text that was processed.
        mode:              Execution mode used — ``"deterministic"`` or ``"ai"``.
        template_id:       Template ID used for rendering.
        presentation_spec: Extracted :class:`~pptgen.spec.presentation_spec.PresentationSpec`.
        slide_plan:        :class:`~pptgen.planner.SlidePlan` from the planning engine.
        deck_definition:   Deck YAML structure (plain dict) from the translator.
        output_path:       Absolute path to the rendered ``.pptx`` file, or ``None``.
        notes:             Optional diagnostic notes (e.g. AI fallback messages).
    """

    stage: str
    playbook_id: str
    input_text: str
    mode: str = field(default=DETERMINISTIC)
    template_id: str | None = field(default=None)
    presentation_spec: PresentationSpec | None = field(default=None)
    slide_plan: SlidePlan | None = field(default=None)
    deck_definition: dict[str, Any] | None = field(default=None)
    output_path: str | None = field(default=None)
    notes: str = field(default="")
    artifact_paths: dict[str, str] | None = field(default=None)
    resolved_style_map: ResolvedStyleMap | None = field(default=None)
    resolved_layout: ResolvedLayout | None = field(default=None)
    resolved_primitive: ResolvedSlidePrimitive | None = field(default=None)
    resolved_assets: list[ResolvedAsset] | None = field(default=None)


def generate_presentation(
    input_text: str,
    output_path: Path | None = None,
    template_id: str | None = None,
    mode: str | ExecutionMode = DETERMINISTIC,
    artifacts_dir: Path | None = None,
    run_context: RunContext | None = None,
    theme_id: str | None = None,
) -> PipelineResult:
    """Entry point for the presentation generation pipeline.

    Args:
        input_text:  Raw text to process.  Leading/trailing whitespace is stripped.
        output_path: If provided, the deck is rendered to this path.
        template_id: Optional template override.  Must be a registered ID.
        mode:         Execution mode — ``"deterministic"`` (default) or ``"ai"``.
                      Accepts either a plain string or an :class:`ExecutionMode` member.
        artifacts_dir: If provided, write ``spec.json``, ``slide_plan.json``,
                       and ``deck_definition.json`` to this directory after the
                       deck is planned.  The directory is created if it does not
                       exist.  When ``None`` (the default), no artifact files are
                       written.
        run_context: Optional :class:`~pptgen.runtime.run_context.RunContext` for
                     stage timing and run metadata.  When provided, stage timings
                     and ``playbook_id`` are populated in-place.
        theme_id:    Optional design system theme identifier (e.g. ``"executive"``).
                     Overrides the platform default theme from settings.  When
                     resolved, ``token.<key>`` references in the deck definition
                     are substituted before rendering.

    Returns:
        :class:`PipelineResult` with ``stage="rendered"`` or ``"deck_planned"``.
        ``PipelineResult.artifact_paths`` is populated when *artifacts_dir* is
        provided.

    Raises:
        InputSizeError: If *input_text* exceeds the configured ``max_input_bytes``.
        PipelineError: If *input_text* is not a string, *template_id* or *mode*
                       is invalid, or any pipeline step fails.
    """
    if not isinstance(input_text, str):
        raise PipelineError(
            f"generate_presentation() expects a str, "
            f"got {type(input_text).__name__!r}."
        )

    # Normalise mode to a plain string for consistent comparison and storage.
    mode_str: str = mode.value if isinstance(mode, ExecutionMode) else mode

    if mode_str not in VALID_STRATEGIES:
        raise PipelineError(
            f"Unknown mode '{mode_str}'.  "
            f"Valid modes: {', '.join(sorted(VALID_STRATEGIES))}."
        )

    normalised = input_text.strip()

    # Input size guard — checked after normalisation.
    settings = get_settings()
    byte_len = len(normalised.encode("utf-8"))
    if byte_len > settings.max_input_bytes:
        raise InputSizeError(
            f"Input exceeds maximum size of {settings.max_input_bytes} bytes "
            f"({byte_len} bytes received)."
        )

    if template_id is not None:
        _validate_template_id(template_id)

    if run_context:
        run_context.start_stage("route_input")
    try:
        playbook_id = route_input(normalised)
    except InputRouterError as exc:
        raise PipelineError(str(exc)) from exc
    finally:
        if run_context:
            run_context.end_stage("route_input")

    if run_context:
        run_context.playbook_id = playbook_id
        run_context.start_stage("execute_playbook")
    try:
        spec, exec_notes = execute_playbook_full(playbook_id, normalised, strategy=mode_str)
    except (PlaybookNotFoundError, UnknownStrategyError) as exc:
        raise PipelineError(str(exc)) from exc
    finally:
        if run_context:
            run_context.end_stage("execute_playbook")

    resolved_template = _resolve_template(playbook_id, template_id, spec.template)
    spec = spec.model_copy(update={"template": resolved_template})

    if run_context:
        run_context.start_stage("plan_slides")
    slide_plan = plan_slides(spec, playbook_id=playbook_id)
    if run_context:
        run_context.end_stage("plan_slides")

    if run_context:
        run_context.start_stage("convert_spec")
    deck_definition = convert_spec_to_deck(spec)
    if run_context:
        run_context.end_stage("convert_spec")

    # Primitive resolution (Phase 9 Stage 3).
    # Reads optional 'primitive' and 'content' keys from deck_definition.
    # On success, injects 'layout' and 'slots' so the layout stage runs normally.
    # Templates without a primitive declaration are unaffected.
    resolved_primitive: ResolvedSlidePrimitive | None = None
    declared_primitive = (
        deck_definition.get("primitive") if isinstance(deck_definition, dict) else None
    )
    if declared_primitive:
        if run_context:
            run_context.start_stage("resolve_primitive")
        try:
            resolved_primitive = _resolve_primitive(
                str(declared_primitive), deck_definition, settings
            )
            # Inject layout + slots so the existing layout stage handles them.
            deck_definition = {
                **deck_definition,
                "layout": resolved_primitive.layout_id,
                "slots": resolved_primitive.resolved_slots,
            }
        except DesignSystemError as exc:
            raise PipelineError(str(exc)) from exc
        finally:
            if run_context:
                run_context.end_stage("resolve_primitive")

    # Layout resolution (Phase 9 Stage 2).
    # Reads optional 'layout' and 'slots' keys from deck_definition.
    # Templates without a layout declaration are unaffected.
    resolved_layout: ResolvedLayout | None = None
    declared_layout = deck_definition.get("layout") if isinstance(deck_definition, dict) else None
    if declared_layout:
        if run_context:
            run_context.start_stage("resolve_layout")
        try:
            resolved_layout = _resolve_layout(
                str(declared_layout), deck_definition, settings
            )
        except DesignSystemError as exc:
            raise PipelineError(str(exc)) from exc
        finally:
            if run_context:
                run_context.end_stage("resolve_layout")

    # Design system token resolution (Phase 9 Stage 1).
    # Precedence: run-time theme_id → settings.default_theme → no theme.
    resolved_style_map: ResolvedStyleMap | None = None
    effective_theme = theme_id or settings.default_theme or ""
    if effective_theme:
        if run_context:
            run_context.start_stage("resolve_tokens")
        try:
            resolved_style_map = _resolve_design_tokens(effective_theme)
            resolver = TokenResolver()
            deck_definition = resolver.resolve_references(deck_definition, resolved_style_map)
        except DesignSystemError as exc:
            raise PipelineError(str(exc)) from exc
        finally:
            if run_context:
                run_context.end_stage("resolve_tokens")

    # Asset resolution (Phase 9 Stage 4).
    # Always runs on valid deck_definition — a no-op when no asset_id refs exist.
    resolved_assets: list[ResolvedAsset] | None = None
    if isinstance(deck_definition, dict):
        if run_context:
            run_context.start_stage("resolve_assets")
        try:
            asset_registry = DesignSystemRegistry(settings.design_system_root)
            deck_definition, resolved_assets = AssetResolver().resolve_references(
                deck_definition, asset_registry
            )
        except DesignSystemError as exc:
            raise PipelineError(str(exc)) from exc
        finally:
            if run_context:
                run_context.end_stage("resolve_assets")

    # Compose diagnostic notes
    notes_parts: list[str] = []
    if not normalised:
        notes_parts.append("no signals matched; routed to fallback")
    if exec_notes:
        notes_parts.append(exec_notes)
    notes = "; ".join(notes_parts)

    # Optional artifact export
    artifact_paths: dict[str, str] | None = None
    if artifacts_dir is not None:
        try:
            raw_paths = write_artifacts(
                Path(artifacts_dir),
                spec,
                slide_plan,
                deck_definition,
            )
            artifact_paths = {k: str(v) for k, v in raw_paths.items()}
            if resolved_style_map is not None:
                snapshot_path = Path(artifacts_dir) / "resolved_theme_snapshot.json"
                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                snapshot_path.write_text(
                    json.dumps(resolved_style_map.to_dict(), indent=2),
                    encoding="utf-8",
                )
                artifact_paths["resolved_theme_snapshot"] = str(snapshot_path)
            if resolved_layout is not None:
                layout_snapshot_path = Path(artifacts_dir) / "resolved_layout_snapshot.json"
                layout_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                layout_snapshot_path.write_text(
                    json.dumps(resolved_layout.to_dict(), indent=2),
                    encoding="utf-8",
                )
                artifact_paths["resolved_layout_snapshot"] = str(layout_snapshot_path)
            if resolved_primitive is not None:
                primitive_snapshot_path = (
                    Path(artifacts_dir) / "resolved_primitive_snapshot.json"
                )
                primitive_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                primitive_snapshot_path.write_text(
                    json.dumps(resolved_primitive.to_dict(), indent=2),
                    encoding="utf-8",
                )
                artifact_paths["resolved_primitive_snapshot"] = str(primitive_snapshot_path)
            if resolved_assets:
                assets_snapshot_path = (
                    Path(artifacts_dir) / "resolved_assets_snapshot.json"
                )
                assets_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                assets_snapshot_path.write_text(
                    json.dumps(
                        {"assets": [a.to_dict() for a in resolved_assets]},
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                artifact_paths["resolved_assets_snapshot"] = str(assets_snapshot_path)
        except OSError as exc:
            raise PipelineError(f"Artifact export failed: {exc}") from exc

    if output_path is None:
        return PipelineResult(
            stage="deck_planned",
            playbook_id=playbook_id,
            input_text=normalised,
            mode=mode_str,
            template_id=resolved_template,
            presentation_spec=spec,
            slide_plan=slide_plan,
            deck_definition=deck_definition,
            notes=notes,
            artifact_paths=artifact_paths,
            resolved_style_map=resolved_style_map,
            resolved_layout=resolved_layout,
            resolved_primitive=resolved_primitive,
            resolved_assets=resolved_assets,
        )

    if run_context:
        run_context.start_stage("render")
    _render(deck_definition, resolved_template, Path(output_path))
    if run_context:
        run_context.end_stage("render")

    return PipelineResult(
        stage="rendered",
        playbook_id=playbook_id,
        input_text=normalised,
        mode=mode_str,
        template_id=resolved_template,
        presentation_spec=spec,
        slide_plan=slide_plan,
        deck_definition=deck_definition,
        output_path=str(output_path),
        notes=notes,
        artifact_paths=artifact_paths,
        resolved_style_map=resolved_style_map,
        resolved_layout=resolved_layout,
        resolved_primitive=resolved_primitive,
        resolved_assets=resolved_assets,
    )


# ---------------------------------------------------------------------------
# Template resolution helpers
# ---------------------------------------------------------------------------

def _resolve_template(
    playbook_id: str,
    override: str | None,
    spec_default: str,
) -> str:
    """Return the template ID to use, applying precedence rules."""
    if override is not None:
        return override
    return get_default_template(playbook_id) or spec_default


def _validate_template_id(template_id: str) -> None:
    """Raise PipelineError if *template_id* is not in the registry."""
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
# Design system helpers
# ---------------------------------------------------------------------------

def _resolve_design_tokens(theme_id: str) -> ResolvedStyleMap:
    """Load the design system and resolve *theme_id* to a :class:`ResolvedStyleMap`.

    Raises:
        DesignSystemError: Propagated to caller — results in a PipelineError.
    """
    settings = get_settings()
    registry = DesignSystemRegistry(settings.design_system_root)
    base = registry.load_base_tokens()
    theme = registry.get_theme(theme_id)
    brand = registry.get_brand(theme.brand_id)
    resolver = TokenResolver()
    return resolver.resolve(base, brand, theme)


def _resolve_primitive(
    primitive_id: str,
    deck_definition: dict[str, Any],
    settings: Any,
) -> ResolvedSlidePrimitive:
    """Load the primitive registry and resolve *primitive_id* against the
    declared content fields.

    Content is read from ``deck_definition["content"]``; an empty dict is used
    when the key is absent (which will fail required-field validation).

    Raises:
        DesignSystemError: Propagated to caller — results in a PipelineError.
    """
    registry = DesignSystemRegistry(settings.design_system_root)
    content = deck_definition.get("content") or {}
    if not isinstance(content, dict):
        content = {}
    resolver = PrimitiveResolver()
    return resolver.resolve(primitive_id, content, registry)


def _resolve_layout(
    layout_id: str,
    deck_definition: dict[str, Any],
    settings: Any,
) -> ResolvedLayout:
    """Load the layout registry and resolve *layout_id* against the declared slots.

    Slots are read from ``deck_definition["slots"]`` if present; an empty list
    is used when the key is absent (will fail required-region validation).

    Raises:
        DesignSystemError: Propagated to caller — results in a PipelineError.
    """
    registry = DesignSystemRegistry(settings.design_system_root)
    raw_slots = deck_definition.get("slots") or {}
    provided_slots = list(raw_slots.keys()) if isinstance(raw_slots, dict) else []
    resolver = LayoutResolver()
    return resolver.resolve(layout_id, provided_slots, registry)


# ---------------------------------------------------------------------------
# Internal rendering helper
# ---------------------------------------------------------------------------

def _render(
    deck_definition: dict[str, Any],
    spec_template: str,
    output_path: Path,
) -> None:
    """Load *deck_definition*, resolve template, and write a .pptx."""
    try:
        deck = parse_deck(deck_definition)
        registry = TemplateRegistry.from_file(_REGISTRY_PATH)
        entry = registry.get(spec_template)
        template_path = _REGISTRY_PATH.parent.parent / entry.path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_deck(deck, template_path, output_path)
    except _PptgenError as exc:
        raise PipelineError(str(exc)) from exc
