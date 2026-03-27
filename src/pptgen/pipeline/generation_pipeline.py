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
        ├─ [if input is structured deck YAML with 'slides' key]
        │   └─ use parsed dict directly   →  deck_definition (bypass extraction)
        ├─ [else: narrative text path]
        │   ├─ convert_spec_to_deck()    →  deck_definition (dict)
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

import yaml

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

    # Structured deck bypass (Phase 9).
    # When input_text is a YAML deck definition (top-level 'slides' list),
    # skip content extraction, spec creation, and slide planning entirely.
    # The Phase 9 resolution stages below handle 'primitive', 'layout',
    # 'content', and asset refs directly from the parsed dict.
    # Narrative text never produces this shape when YAML-parsed.
    _structured = _try_parse_deck_definition(normalised)

    if _structured is not None:
        _validate_structured_deck_shape(_structured)
        deck_definition: dict[str, Any] = _structured
        playbook_id = "direct-deck-input"
        spec = None
        slide_plan = None
        exec_notes = ""
        _deck_meta = _structured.get("deck") if isinstance(_structured.get("deck"), dict) else {}
        # Prefer deck.template (legacy shape); fall back to top-level template
        # (Phase 9 root shape has no 'deck' wrapper); then platform default.
        resolved_template = (
            template_id
            or _deck_meta.get("template", "")
            or (_structured.get("template", "") if isinstance(_structured.get("template"), str) else "")
            or "ops_review_v1"
        )
        if run_context:
            run_context.playbook_id = playbook_id
    else:
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
            artifacts_dir_path = Path(artifacts_dir)
            if spec is not None and slide_plan is not None:
                raw_paths = write_artifacts(
                    artifacts_dir_path,
                    spec,
                    slide_plan,
                    deck_definition,
                )
                artifact_paths = {k: str(v) for k, v in raw_paths.items()}
            else:
                # Direct deck input: no spec or plan — write only the
                # resolved deck definition.
                artifacts_dir_path.mkdir(parents=True, exist_ok=True)
                deck_path = artifacts_dir_path / "deck_definition.json"
                deck_path.write_text(
                    json.dumps(deck_definition, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                artifact_paths = {"deck_definition": str(deck_path)}
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
# Structured deck detection and validation
# ---------------------------------------------------------------------------

# All top-level keys that a valid structured deck definition may contain.
# Any key outside this set is an orphan (e.g. a mis-placed content block)
# and should be rejected before the Phase 9 resolution stages run.
_ALLOWED_STRUCTURED_DECK_KEYS: frozenset[str] = frozenset({
    # Legacy deck wrapper and slides list
    "deck", "slides",
    # Phase 9 root-format metadata fields (promoted into deck by normalizer)
    "title", "subtitle", "author", "template",
    "version", "date", "status", "description", "tags",
    # Phase 9 top-level resolution fields
    "primitive", "theme", "content", "layout", "slots",
})


def _validate_structured_deck_shape(data: dict) -> None:
    """Raise :class:`PipelineError` if *data* is not a well-formed structured deck.

    Called immediately after :func:`_try_parse_deck_definition` succeeds, before
    any Phase 9 resolution stage runs.  This converts downstream ``TypeError`` /
    ``AttributeError`` failures into an explicit HTTP 400 ``PipelineError``.

    Validation rules (minimal — do not over-constrain valid Phase 9 input):

    1. No unknown top-level keys.  Known keys are listed in
       ``_ALLOWED_STRUCTURED_DECK_KEYS``.  Orphan blocks (e.g. an ``icon:`` or
       ``component:`` key placed at root level) are rejected here rather than
       silently leaking into asset resolution.

    2. ``slides`` is non-empty.  A deck with zero slides cannot produce a
       presentation and is structurally invalid.

    3. Every element of ``slides`` is a mapping (dict).  Scalar or list entries
       would cause ``TypeError`` deep in the pipeline.

    4. Every slide has ``type`` or ``primitive``.  Slides with neither cannot be
       dispatched by the schema discriminator and produce confusing errors later.
    """
    unknown = set(data) - _ALLOWED_STRUCTURED_DECK_KEYS
    if unknown:
        raise PipelineError(
            f"Structured deck input contains unexpected top-level key(s): "
            f"{sorted(unknown)}.  "
            f"Remove orphan keys or move content under 'slides'."
        )

    slides = data.get("slides")
    if not slides:
        raise PipelineError(
            "Structured deck input has an empty 'slides' list.  "
            "Provide at least one slide with a 'type' or 'primitive' key."
        )

    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            raise PipelineError(
                f"Structured deck: slide {i} is not a mapping "
                f"(got {type(slide).__name__}).  Each slide must be a YAML mapping."
            )
        if "type" not in slide and "primitive" not in slide:
            raise PipelineError(
                f"Structured deck: slide {i} has neither 'type' nor 'primitive'.  "
                f"Every slide must declare one of these keys."
            )


def _try_parse_deck_definition(text: str) -> dict[str, Any] | None:
    """Return a parsed deck definition dict if *text* is structured deck YAML.

    A structured deck definition is identified by a top-level ``slides`` key
    whose value is a list.  This shape never appears in narrative text input
    (meeting notes, ADO summaries, etc.) when YAML-parsed, making it a safe
    discriminator.

    Returns ``None`` for any input that is not a structured deck definition:
    YAML parse failure, non-dict result, missing or non-list ``slides`` key.
    """
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("slides"), list):
        return None
    return data


# ---------------------------------------------------------------------------
# Primitive-slide normalisation (pre-render)
# ---------------------------------------------------------------------------

# Only MetricItem fields survive the strip — MetricItem.extra="forbid" rejects
# any extra keys such as resolved asset dicts injected into metric items.
_METRIC_ITEM_FIELDS: frozenset[str] = frozenset({"label", "value", "unit"})

# Maps each Phase 9 primitive ID to the legacy type string the renderer knows.
_PRIMITIVE_TO_LEGACY_TYPE: dict[str, str] = {
    "title_slide":      "title",
    "section_slide":    "section",
    "bullet_slide":     "bullets",
    "summary_slide":    "bullets",
    "comparison_slide": "two_column",
    "metrics_slide":    "metric_summary",
    "image_text_slide": "image_caption",
}


def _primitive_slide_to_legacy(slide: dict[str, Any]) -> dict[str, Any]:
    """Return a legacy slide dict for a single ``primitive:``-keyed slide.

    Converts Phase 9 semantic content fields to the exact field names expected
    by the Pydantic slide models and slide renderers.  Called by
    :func:`_normalize_primitive_slides` for every slide that carries a
    ``primitive`` key.
    """
    primitive: str = slide.get("primitive", "")
    content: dict[str, Any] = slide.get("content") or {}
    # Preserve bookkeeping fields that exist on every slide base
    base: dict[str, Any] = {
        k: slide[k] for k in ("id", "notes", "visible") if k in slide
    }
    base.setdefault("visible", True)

    if primitive == "title_slide":
        return {
            **base,
            "type": "title",
            "title": str(content.get("title") or ""),
            # subtitle is Field(min_length=1) — use a single space when absent
            "subtitle": str(content.get("subtitle") or " "),
        }

    if primitive == "section_slide":
        return {
            **base,
            "type": "section",
            "section_title": str(
                content.get("heading") or content.get("title") or ""
            ),
            "section_subtitle": str(content.get("description") or "") or None,
        }

    if primitive in ("bullet_slide", "summary_slide"):
        raw_bullets = content.get("bullets") or content.get("key_points") or []
        bullets = [str(b) for b in raw_bullets if b is not None] or ["(no content)"]
        return {
            **base,
            "type": "bullets",
            "title": str(content.get("title") or ""),
            "bullets": bullets,
        }

    if primitive == "comparison_slide":
        # Accept both nested shape ({left: {title, bullets}}) and flat shape
        # ({left_title, left_points}).
        if "left" in content and isinstance(content["left"], dict):
            left = content["left"]
            right = content.get("right") or {}
            title = str(left.get("title") or content.get("title") or "")
            left_c = [str(x) for x in (left.get("points") or left.get("bullets") or [])]
            right_c = [str(x) for x in (right.get("points") or right.get("bullets") or [])]
        else:
            title = str(content.get("left_title") or content.get("title") or "")
            left_c = [str(x) for x in (content.get("left_points") or content.get("left_content") or [])]
            right_c = [str(x) for x in (content.get("right_points") or content.get("right_content") or [])]
        # left_content/right_content are Field(min_length=1) — must have ≥1 item
        return {
            **base,
            "type": "two_column",
            "title": title or " ",
            "left_content":  left_c  or ["—"],
            "right_content": right_c or ["—"],
        }

    if primitive == "metrics_slide":
        raw_metrics = content.get("metrics") or []
        # Strip extra fields (e.g. asset-resolved icon dicts) — MetricItem.extra="forbid"
        metrics = [
            {k: v for k, v in m.items() if k in _METRIC_ITEM_FIELDS}
            for m in raw_metrics
            if isinstance(m, dict) and "label" in m and "value" in m
        ]
        return {
            **base,
            "type": "metric_summary",
            "title": str(content.get("title") or ""),
            "metrics": metrics or [{"label": "—", "value": "—"}],
        }

    if primitive == "image_text_slide":
        image = content.get("image") or {}
        # After asset resolution, image dict contains resolved_source
        image_path = (
            str(image.get("resolved_source") or image.get("url") or "")
            if isinstance(image, dict)
            else str(image)
        )
        description = content.get("description") or {}
        caption = (
            str(description.get("text") or "")
            if isinstance(description, dict)
            else str(description)
        )
        return {
            **base,
            "type": "image_caption",
            "title":      str(content.get("title") or ""),
            "image_path": image_path or " ",
            "caption":    caption    or " ",
        }

    # Unknown primitive — emit a blank title slide rather than crashing.
    return {
        **base,
        "type": "title",
        "title":    str(content.get("title") or f"[{primitive}]"),
        "subtitle": " ",
    }


def _normalize_primitive_slides(deck_definition: dict[str, Any]) -> dict[str, Any]:
    """Convert every per-slide ``primitive:`` entry to its legacy ``type:`` equivalent.

    The renderer only understands legacy type-discriminated slides.  This
    function is called immediately before :func:`parse_deck` inside
    :func:`_render` so that fully-resolved Phase 9 primitive slides (after
    token/asset resolution) are translated into the exact shapes the Pydantic
    slide models and slide renderers expect.

    Slides that already carry a ``type:`` key are passed through unchanged
    (full backward compatibility).  If no ``primitive``-keyed slides are
    present the original dict is returned without copying.
    """
    slides = deck_definition.get("slides")
    if not isinstance(slides, list):
        return deck_definition

    if not any(isinstance(s, dict) and "primitive" in s for s in slides):
        return deck_definition  # fast path — no primitive slides

    normalized_slides = [
        _primitive_slide_to_legacy(s)
        if (isinstance(s, dict) and "primitive" in s)
        else s
        for s in slides
    ]
    return {**deck_definition, "slides": normalized_slides}


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
        normalized = _normalize_primitive_slides(deck_definition)
        deck = parse_deck(normalized)
        registry = TemplateRegistry.from_file(_REGISTRY_PATH)
        entry = registry.get(spec_template)
        template_path = _REGISTRY_PATH.parent.parent / entry.path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_deck(deck, template_path, output_path)
    except _PptgenError as exc:
        raise PipelineError(str(exc)) from exc
