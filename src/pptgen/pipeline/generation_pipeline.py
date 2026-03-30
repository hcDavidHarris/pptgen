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
import uuid
from dataclasses import dataclass, field
from dataclasses import replace as _dc_replace
from datetime import date, datetime, timezone
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
    ResolvedArtifactDependency,
    ResolvedAsset,
    ResolvedLayout,
    ResolvedSlidePrimitive,
    ResolvedStyleMap,
    TokenResolver,
)
from ..analytics import (
    ArtifactUsageEvent,
    ArtifactUsageRecord,
    FailureAttribution,
    GovernanceAuditEvent,
    GovernanceTelemetryCollector,
    RunFailureAttribution,
    RunRecord,
)
from ..analytics.aggregate_summarizer import update_daily_aggregates
from ..analytics.writer import (
    update_aggregates,
    write_audit_events,
    write_failure_attribution,
    write_run_record,
    write_usage_events,
    write_usage_snapshot,
)
from ..design_system.dependency_models import record_dependency
from ..design_system.exceptions import DesignSystemError, GovernanceViolationError
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
from ..content_intelligence import (
    ContentIntent,
    EnrichedSlideContent,
    normalize_for_pipeline,
    run_content_intelligence,
)


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
    governance_warnings: list[str] = field(default_factory=list)
    dependency_chain: list[ResolvedArtifactDependency] = field(default_factory=list)
    # Phase 10D.2 — analytics identifiers.
    #: UUID generated at the start of the pipeline run.  Empty string only
    #: when PipelineResult is constructed outside of generate_presentation()
    #: (e.g. in tests that build the dataclass directly).
    run_id: str = field(default="")
    #: Always ``None`` on the success path — PipelineResult is only returned
    #: when the run completes without exception.  Present as a field so that
    #: Phase 10D.3 can embed it in RunRecord for correlation.
    failure_attribution: FailureAttribution | None = field(default=None)
    # Phase 10D.3 — per-run analytics records.
    #: Top-level summary of this run.  Always set by generate_presentation().
    #: ``None`` only when PipelineResult is constructed directly (e.g. tests).
    run_record: RunRecord | None = field(default=None)
    #: One :class:`~pptgen.analytics.ArtifactUsageEvent` per entry in
    #: :attr:`dependency_chain`.  Empty when no governed artifacts were resolved.
    usage_events: list[ArtifactUsageEvent] = field(default_factory=list)
    #: Governance audit events emitted during this run (draft overrides and
    #: deprecated-artifact uses).  ``run_id`` is backfilled on all events.
    #: Empty when no overrides or deprecations occurred.
    #: Sourced from GovernanceTelemetryCollector.get_audit_events() after run.
    # TODO(10D): consider reducing to summary/path instead of full payload once
    #            a persistent store is in place (Phase 10D.6+).
    audit_events: list[GovernanceAuditEvent] = field(default_factory=list)
    #: Phase 10D.4 — richer per-artifact usage records, one per distinct
    #: (artifact_type, artifact_family, artifact_version, usage_scope) seen.
    #: Finalised (run_id backfilled, success/failure flag set) before return.
    #: Empty when no governed artifacts were resolved.
    usage_records: list[ArtifactUsageRecord] = field(default_factory=list)
    #: Phase 11A — enriched content produced by the content intelligence layer.
    #: Populated when a ContentIntent is supplied to generate_presentation().
    #: None when the CI layer is not invoked (default — non-breaking).
    enriched_content: list[EnrichedSlideContent] | None = field(default=None)


def generate_presentation(
    input_text: str,
    output_path: Path | None = None,
    template_id: str | None = None,
    mode: str | ExecutionMode = DETERMINISTIC,
    artifacts_dir: Path | None = None,
    run_context: RunContext | None = None,
    theme_id: str | None = None,
    content_intent: ContentIntent | None = None,
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

    # Phase 10D.2 / 10D.3 — generate a UUID and capture start time for this run.
    # run_id is the correlation key across PipelineResult, RunRecord,
    # ArtifactUsageEvent, and GovernanceAuditEvent.
    run_id = str(uuid.uuid4())
    run_start_utc = datetime.now(timezone.utc)
    # Populated inside each resolution-stage except block before re-raising.
    # Remains None on the success path (PipelineResult is only returned then).
    # Phase 10D.3 reads this to embed in RunRecord.
    _failure_attribution: FailureAttribution | None = None

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

    # Content intelligence enriched output — populated by the CI branch only.
    # None on the structured-bypass and legacy paths.
    _enriched_content: list[EnrichedSlideContent] | None = None

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
        # When a ContentIntent is also provided alongside a structured deck,
        # run CI for enrichment and observability.  The structured deck still
        # drives the rendered slides; CI output is carried in enriched_content.
        if content_intent is not None:
            if run_context:
                run_context.start_stage("content_intelligence")
            _enriched_content = run_content_intelligence(content_intent)
            if run_context:
                run_context.end_stage("content_intelligence")

    elif content_intent is not None:
        # Content Intelligence path (Phase 11C).
        # When a ContentIntent is supplied, the CI layer owns deck building.
        # The legacy playbook / planning / spec-to-deck path is bypassed entirely
        # to prevent raw input-text (which may be a stringified ContentIntent)
        # from reaching slide content via the rule-based extractors.
        playbook_id = "content-intelligence"
        spec = None
        slide_plan = None
        exec_notes = ""
        resolved_template = template_id or "ops_review_v1"
        if run_context:
            run_context.playbook_id = playbook_id
            run_context.start_stage("content_intelligence")
        _enriched_content = run_content_intelligence(content_intent)
        if run_context:
            run_context.end_stage("content_intelligence")
        deck_definition = _build_deck_from_enriched_content(
            content_intent, _enriched_content, resolved_template
        )

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

    # Governance warnings and dependency chain accumulated across all resolution
    # stages (Phase 10B / 10C).  The telemetry collector owns audit events.
    governance_warnings: list[str] = []
    dependency_chain: list[ResolvedArtifactDependency] = []
    # Phase 10D.5/10D.4 — one collector per run; passed (as telemetry=) to helpers.
    _telemetry = GovernanceTelemetryCollector(run_ts=run_start_utc)

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
                str(declared_primitive), deck_definition, settings,
                governance_warnings, dependency_chain, _telemetry,
            )
            # Inject layout + slots so the existing layout stage handles them.
            deck_definition = {
                **deck_definition,
                "layout": resolved_primitive.layout_id,
                "slots": resolved_primitive.resolved_slots,
            }
        except (DesignSystemError, GovernanceViolationError) as exc:
            _failure_attribution = FailureAttribution(
                stage="primitive",
                artifact_type="primitive",
                artifact_id=str(declared_primitive),
                error_type=type(exc).__name__,
            )
            _telemetry.record_failure_context(
                exc, candidate_type="primitive",
                candidate_family=str(declared_primitive),
                candidate_version=None,
            )
            _telemetry.finalize_usage(False, run_id=run_id)
            _write_failure_telemetry_nonblocking(
                _telemetry, settings, run_id, run_start_utc.date()
            )
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
                str(declared_layout), deck_definition, settings,
                governance_warnings, dependency_chain, _telemetry,
                layout_usage_scope="dependency" if declared_primitive else "top_level",
            )
        except (DesignSystemError, GovernanceViolationError) as exc:
            _failure_attribution = FailureAttribution(
                stage="layout",
                artifact_type="layout",
                artifact_id=str(declared_layout),
                error_type=type(exc).__name__,
            )
            _telemetry.record_failure_context(
                exc, candidate_type="layout",
                candidate_family=str(declared_layout),
                candidate_version=None,
            )
            _telemetry.finalize_usage(False, run_id=run_id)
            _write_failure_telemetry_nonblocking(
                _telemetry, settings, run_id, run_start_utc.date()
            )
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
            resolved_style_map = _resolve_design_tokens(
                effective_theme, settings, governance_warnings, dependency_chain,
                _telemetry,
                theme_resolution_source="explicit" if theme_id else "default",
            )
            resolver = TokenResolver()
            deck_definition = resolver.resolve_references(deck_definition, resolved_style_map)
        except (DesignSystemError, GovernanceViolationError) as exc:
            _failure_attribution = FailureAttribution(
                stage="theme",
                artifact_type="theme",
                artifact_id=effective_theme,
                error_type=type(exc).__name__,
            )
            _telemetry.record_failure_context(
                exc, candidate_type="theme",
                candidate_family=effective_theme,
                candidate_version=None,
            )
            _telemetry.finalize_usage(False, run_id=run_id)
            _write_failure_telemetry_nonblocking(
                _telemetry, settings, run_id, run_start_utc.date()
            )
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
                deck_definition, asset_registry,
                allow_draft=settings.allow_draft_artifacts,
                governance_warnings=governance_warnings,
                dependency_chain=dependency_chain,
            )
        except (DesignSystemError, GovernanceViolationError) as exc:
            _failure_attribution = FailureAttribution(
                stage="asset",
                artifact_type="asset",
                artifact_id=None,  # multiple assets may be in flight
                error_type=type(exc).__name__,
            )
            _telemetry.record_failure_context(
                exc, candidate_type="asset",
                candidate_family=None,
                candidate_version=None,
            )
            _telemetry.finalize_usage(False, run_id=run_id)
            _write_failure_telemetry_nonblocking(
                _telemetry, settings, run_id, run_start_utc.date()
            )
            raise PipelineError(str(exc)) from exc
        finally:
            if run_context:
                run_context.end_stage("resolve_assets")

    # Per-slide primitive governance — Phase 10C patch.
    if isinstance(deck_definition, dict):
        try:
            _enforce_per_slide_primitive_governance(
                deck_definition, settings, governance_warnings, dependency_chain,
                _telemetry,
            )
        except (DesignSystemError, GovernanceViolationError) as exc:
            _failure_attribution = FailureAttribution(
                stage="primitive",
                artifact_type="primitive",
                artifact_id=None,  # multiple per-slide primitives may be in flight
                error_type=type(exc).__name__,
            )
            _telemetry.record_failure_context(
                exc, candidate_type="primitive",
                candidate_family=None,
                candidate_version=None,
            )
            _telemetry.finalize_usage(False, run_id=run_id)
            _write_failure_telemetry_nonblocking(
                _telemetry, settings, run_id, run_start_utc.date()
            )
            raise PipelineError(str(exc)) from exc

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
        _telemetry.mark_stage("export")
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
            elif content_intent is not None and _enriched_content is not None:
                # CI path — emit spec.json, slide_plan.json, deck_definition.json
                artifacts_dir_path.mkdir(parents=True, exist_ok=True)
                ci_spec = _build_ci_spec(content_intent, _enriched_content)
                ci_plan = _build_ci_slide_plan(_enriched_content, playbook_id)
                spec_path = artifacts_dir_path / "spec.json"
                plan_path = artifacts_dir_path / "slide_plan.json"
                deck_path = artifacts_dir_path / "deck_definition.json"
                spec_path.write_text(
                    json.dumps(ci_spec, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                plan_path.write_text(
                    json.dumps(ci_plan, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                deck_path.write_text(
                    json.dumps(deck_definition, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                artifact_paths = {
                    "spec": str(spec_path),
                    "slide_plan": str(plan_path),
                    "deck_definition": str(deck_path),
                }
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
            if dependency_chain:
                dep_snapshot_path = (
                    Path(artifacts_dir) / "resolved_dependencies_snapshot.json"
                )
                dep_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                dep_snapshot_path.write_text(
                    json.dumps(
                        {"dependencies": [d.to_dict() for d in dependency_chain]},
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                artifact_paths["resolved_dependencies_snapshot"] = str(dep_snapshot_path)
        except OSError as exc:
            _telemetry.record_failure_context(exc)
            _telemetry.finalize_usage(False, run_id=run_id)
            _write_failure_telemetry_nonblocking(
                _telemetry, settings, run_id, run_start_utc.date()
            )
            raise PipelineError(f"Artifact export failed: {exc}") from exc

    # Phase 10D.3 — build per-run analytics records on the success path.
    # usage_events is derived once here (same for both return branches).
    # RunRecord is constructed inline at each return with the correct stage_reached.
    # Phase 10D.5 — drain the telemetry collector and backfill run_id into the
    # frozen GovernanceAuditEvent instances before attaching to PipelineResult.
    # Phase 10D.4 — finalise usage records (backfill run_id, set success flag).
    _usage_events = _build_usage_events(dependency_chain, run_id, True, settings)
    _backfilled_audit = _backfill_run_id(_telemetry.get_audit_events(), run_id)
    _telemetry.finalize_usage(True, run_id=run_id)

    if output_path is None:
        _result = PipelineResult(
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
            governance_warnings=governance_warnings,
            dependency_chain=dependency_chain,
            run_id=run_id,
            run_record=RunRecord(
                run_id=run_id,
                timestamp_utc=run_start_utc,
                mode=mode_str,
                playbook_id=playbook_id,
                template_id=resolved_template,
                theme_id=theme_id,
                stage_reached="deck_planned",
                succeeded=True,
                failure_attribution=None,
                draft_override_active=settings.allow_draft_artifacts,
                dependency_count=len(dependency_chain),
            ),
            usage_events=_usage_events,
            audit_events=_backfilled_audit,
            usage_records=_telemetry.get_usage_records(),
            enriched_content=_enriched_content,
        )
        _write_telemetry_outputs_nonblocking(_result, settings)
        return _result

    _telemetry.mark_stage("render")
    if run_context:
        run_context.start_stage("render")
    _render(deck_definition, resolved_template, Path(output_path))
    if run_context:
        run_context.end_stage("render")

    _result = PipelineResult(
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
        governance_warnings=governance_warnings,
        dependency_chain=dependency_chain,
        run_id=run_id,
        run_record=RunRecord(
            run_id=run_id,
            timestamp_utc=run_start_utc,
            mode=mode_str,
            playbook_id=playbook_id,
            template_id=resolved_template,
            theme_id=theme_id,
            stage_reached="rendered",
            succeeded=True,
            failure_attribution=None,
            draft_override_active=settings.allow_draft_artifacts,
            dependency_count=len(dependency_chain),
        ),
        usage_events=_usage_events,
        audit_events=_backfilled_audit,
        usage_records=_telemetry.get_usage_records(),
        enriched_content=_enriched_content,
    )
    _write_telemetry_outputs_nonblocking(_result, settings)
    return _result


# ---------------------------------------------------------------------------
# Content Intelligence deck builder (Phase 11C)
# ---------------------------------------------------------------------------

def _build_deck_from_enriched_content(
    content_intent: ContentIntent,
    enriched_slides: list[EnrichedSlideContent],
    resolved_template: str = "ops_review_v1",
) -> dict[str, Any]:
    """Build a deck definition from content intelligence output.

    Converts ``list[EnrichedSlideContent]`` into the deck-definition dict
    expected by the governance / resolution / render stages.

    Design guarantees:
    - Raw ``ContentIntent`` fields are never serialized into slide text.
      Only structured enriched-content fields (title, assertion,
      supporting_points, implications) reach the deck definition.
    - Each ``EnrichedSlideContent`` becomes a ``bullets``-type slide so
      the existing renderer can handle it without changes.
    - The CI metadata (_ci_metadata) is carried for observability in the
      stored deck_definition, but is stripped by _render() before parse_deck()
      because BulletsSlide uses extra='forbid'.

    Args:
        content_intent:    The original authoring intent (topic, goal, audience).
        enriched_slides:   Fully-enriched slide content from the CI pipeline.
        resolved_template: Template ID to embed in deck.template (required by
                           DeckMetadata; default is the platform fallback).

    Returns:
        A deck-definition dict compatible with the existing pipeline.
    """
    topic = content_intent.topic
    # TitleSlide.subtitle is a required non-empty str; fall back to topic.
    subtitle = content_intent.goal or topic

    slides: list[dict[str, Any]] = []

    # Title slide — topic is the title; goal (if any) is the subtitle.
    # Neither field contains raw ContentIntent serialization.
    slides.append({
        "type": "title",
        "title": topic,
        "subtitle": subtitle,
    })

    # One content slide per EnrichedSlideContent.
    for enriched in enriched_slides:
        normalized = normalize_for_pipeline(enriched)
        slide: dict[str, Any] = {
            "type": "bullets",
            "title": normalized["title"],
            "bullets": normalized["bullets"],
            # _ci_metadata is internal-only for observability.
            # Stripped by _render() before parse_deck() (extra='forbid').
            "_ci_metadata": normalized["_ci_metadata"],
        }
        if normalized["notes"]:
            slide["notes"] = normalized["notes"]
        slides.append(slide)

    return {
        "deck": {
            "title": topic,
            "template": resolved_template,
            "author": "pptgen",
        },
        "slides": slides,
    }


# ---------------------------------------------------------------------------
# CI artifact serializers (Phase 11D)
# ---------------------------------------------------------------------------

def _build_ci_spec(
    content_intent: ContentIntent,
    enriched_slides: list[EnrichedSlideContent],
) -> dict[str, Any]:
    """Build a CI-native spec dict from a ContentIntent and enriched slides.

    This is the CI equivalent of ``PresentationSpec`` — a structured record of
    what the content intelligence layer produced, suitable for storing as
    ``spec.json`` in the artifact directory.

    Args:
        content_intent:  The original authoring intent.
        enriched_slides: Fully-enriched slide content from the CI pipeline.

    Returns:
        Serializable dict with ``source_mode``, intent fields, and per-slide
        structured content.
    """
    slides = []
    for i, slide in enumerate(enriched_slides):
        slides.append({
            "index": i,
            "title": slide.title,
            "assertion": slide.assertion or "",
            "supporting_points": list(slide.supporting_points),
            "implications": list(slide.implications or []),
            "intent_type": slide.metadata.get("intent_type", ""),
            "primitive": slide.primitive or "",
        })
    return {
        "source_mode": "content_intelligence",
        "topic": content_intent.topic,
        "goal": content_intent.goal or "",
        "audience": content_intent.audience or "",
        "slide_count": len(enriched_slides),
        "slides": slides,
    }


def _build_ci_slide_plan(
    enriched_slides: list[EnrichedSlideContent],
    playbook_id: str = "content-intelligence",
) -> dict[str, Any]:
    """Build a CI-native slide plan dict from enriched slides.

    This is the CI equivalent of ``SlidePlan`` — a per-slide record of intent,
    primitive, prompt backend, and fallback state.  Stored as ``slide_plan.json``
    in the artifact directory.

    The first slide in the deck is always the title slide; remaining slides are
    bullets slides.  ``slide_type`` reflects this assignment.

    Args:
        enriched_slides: Fully-enriched slide content from the CI pipeline.
        playbook_id:     Playbook identifier to embed in the plan.

    Returns:
        Serializable dict with deck-level metadata and per-slide plan entries.
    """
    slide_entries = []
    for i, slide in enumerate(enriched_slides):
        diag: dict = slide.metadata.get("_prompt_diag", {})
        slide_entries.append({
            "index": i,
            "title": slide.title,
            "intent_type": slide.metadata.get("intent_type", ""),
            "primitive": slide.primitive or "",
            "slide_type": "title" if i == 0 else "bullets",
            "insights_applied": bool(slide.metadata.get("insights_applied", False)),
            "prompt_backend": diag.get("backend", ""),
            "fallback_used": bool(diag.get("fallback_used", False)),
            "fallback_reason": diag.get("fallback_reason", ""),
        })
    return {
        "playbook_id": playbook_id,
        "mode": "content_intelligence",
        "slide_count": len(enriched_slides),
        "slides": slide_entries,
    }


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

def _resolve_design_tokens(
    theme_id: str,
    settings: Any,
    governance_warnings: list[str] | None = None,
    dependency_chain: list[ResolvedArtifactDependency] | None = None,
    telemetry: GovernanceTelemetryCollector | None = None,
    theme_resolution_source: str = "explicit",
) -> ResolvedStyleMap:
    """Load the design system and resolve *theme_id* to a :class:`ResolvedStyleMap`.

    Records two dependencies when *dependency_chain* is provided:

    1. ``token_set/base`` — captured after lifecycle enforcement on the base
       token set.  The base token set carries no governance block in current
       YAML files, so enforcement is a no-op today but will activate
       automatically if a governance block is added in future.
    2. ``theme/<id>``     — captured after lifecycle enforcement on the theme.

    Raises:
        DesignSystemError: Propagated to caller — results in a PipelineError.
        GovernanceViolationError: When the token set or theme is DRAFT and
            allow_draft is False.
    """
    registry = DesignSystemRegistry(settings.design_system_root)
    base = registry.load_base_tokens()
    # Enforce and capture token_set — same pattern as every other artifact type.
    # In practice the base token set carries no governance block today (no-op),
    # but the enforcement call ensures a deprecated token set would both warn
    # and appear in dependency_chain with the correct lifecycle_status.
    _eff_telemetry = telemetry if telemetry is not None else GovernanceTelemetryCollector()
    _eff_warnings = governance_warnings if governance_warnings is not None else []
    _enforce_with_audit(
        registry, "token_set", "base", base.version,
        allow_draft=settings.allow_draft_artifacts,
        governance_warnings=_eff_warnings,
        telemetry=_eff_telemetry,
        usage_scope="dependency",
        resolution_source="explicit",
    )
    if dependency_chain is not None:
        token_gov = registry.get_artifact_governance(
            "token_set", "base", base.version
        )
        record_dependency(
            dependency_chain,
            "token_set", "base", base.version,
            token_gov.lifecycle_status.value if token_gov else None,
            "token_set",
        )
    theme = registry.get_theme(theme_id)
    _enforce_with_audit(
        registry, "theme", theme.theme_id, theme.version,
        allow_draft=settings.allow_draft_artifacts,
        governance_warnings=_eff_warnings,
        telemetry=_eff_telemetry,
        usage_scope="top_level",
        resolution_source=theme_resolution_source,
    )
    if dependency_chain is not None:
        theme_gov = registry.get_artifact_governance(
            "theme", theme.theme_id, theme.version
        )
        record_dependency(
            dependency_chain,
            "theme", theme.theme_id, theme.version,
            theme_gov.lifecycle_status.value if theme_gov else None,
            "theme",
        )
    brand = registry.get_brand(theme.brand_id)
    resolver = TokenResolver()
    return resolver.resolve(base, brand, theme)


def _resolve_primitive(
    primitive_id: str,
    deck_definition: dict[str, Any],
    settings: Any,
    governance_warnings: list[str] | None = None,
    dependency_chain: list[ResolvedArtifactDependency] | None = None,
    telemetry: GovernanceTelemetryCollector | None = None,
) -> ResolvedSlidePrimitive:
    """Load the primitive registry and resolve *primitive_id* against the
    declared content fields.

    Content is read from ``deck_definition["content"]``; an empty dict is used
    when the key is absent (which will fail required-field validation).

    Raises:
        DesignSystemError: Propagated to caller — results in a PipelineError.
        GovernanceViolationError: When primitive is DRAFT and allow_draft is False.
    """
    registry = DesignSystemRegistry(settings.design_system_root)
    content = deck_definition.get("content") or {}
    if not isinstance(content, dict):
        content = {}
    resolver = PrimitiveResolver()
    resolved = resolver.resolve(primitive_id, content, registry)
    _enforce_with_audit(
        registry, "primitive", primitive_id, resolved.primitive_version,
        allow_draft=settings.allow_draft_artifacts,
        governance_warnings=governance_warnings if governance_warnings is not None else [],
        telemetry=telemetry if telemetry is not None else GovernanceTelemetryCollector(),
        usage_scope="top_level",
        resolution_source="explicit",
    )
    if dependency_chain is not None:
        gov = registry.get_artifact_governance(
            "primitive", primitive_id, resolved.primitive_version
        )
        record_dependency(
            dependency_chain,
            "primitive", primitive_id, resolved.primitive_version,
            gov.lifecycle_status.value if gov else None,
            "primitive",
        )
    return resolved


def _resolve_layout(
    layout_id: str,
    deck_definition: dict[str, Any],
    settings: Any,
    governance_warnings: list[str] | None = None,
    dependency_chain: list[ResolvedArtifactDependency] | None = None,
    telemetry: GovernanceTelemetryCollector | None = None,
    layout_usage_scope: str = "top_level",
) -> ResolvedLayout:
    """Load the layout registry and resolve *layout_id* against the declared slots.

    Slots are read from ``deck_definition["slots"]`` if present; an empty list
    is used when the key is absent (will fail required-region validation).

    Raises:
        DesignSystemError: Propagated to caller — results in a PipelineError.
        GovernanceViolationError: When layout is DRAFT and allow_draft is False.
    """
    registry = DesignSystemRegistry(settings.design_system_root)
    raw_slots = deck_definition.get("slots") or {}
    provided_slots = list(raw_slots.keys()) if isinstance(raw_slots, dict) else []
    resolver = LayoutResolver()
    resolved = resolver.resolve(layout_id, provided_slots, registry)
    _enforce_with_audit(
        registry, "layout", layout_id, resolved.layout_version,
        allow_draft=settings.allow_draft_artifacts,
        governance_warnings=governance_warnings if governance_warnings is not None else [],
        telemetry=telemetry if telemetry is not None else GovernanceTelemetryCollector(),
        usage_scope=layout_usage_scope,
        resolution_source="explicit",
    )
    if dependency_chain is not None:
        gov = registry.get_artifact_governance(
            "layout", layout_id, resolved.layout_version
        )
        record_dependency(
            dependency_chain,
            "layout", layout_id, resolved.layout_version,
            gov.lifecycle_status.value if gov else None,
            "layout",
        )
    return resolved


# ---------------------------------------------------------------------------
# Per-slide primitive governance — Phase 10C patch
# ---------------------------------------------------------------------------

def _enforce_per_slide_primitive_governance(
    deck_definition: dict[str, Any],
    settings: Any,
    governance_warnings: list[str],
    dependency_chain: list[ResolvedArtifactDependency],
    telemetry: GovernanceTelemetryCollector | None = None,
) -> None:
    """Enforce lifecycle and record dependency for per-slide ``primitive:`` entries.

    The main resolution stages only inspect the **top-level** ``primitive:`` key
    of ``deck_definition``.  Per-slide primitives — slide dicts inside
    ``deck_definition["slides"]`` that carry a ``primitive:`` key — were
    previously invisible to governance.  This helper closes that gap.

    Algorithm
    ---------
    1. Walk ``deck_definition["slides"]``.
    2. For each slide dict with a ``primitive:`` string key, collect unique IDs
       (``seen_in_slides`` prevents re-processing the same primitive ID for
       every slide that uses it).
    3. Load the primitive YAML once per ID via ``registry.get_primitive()`` to
       obtain the version string.  If the primitive cannot be loaded (unknown or
       malformed YAML), skip silently — the error will surface at render time
       through ``_normalize_primitive_slides()``.
    4. Enforce lifecycle *only* when the primitive is not already present in
       ``dependency_chain`` (i.e. not already enforced via top-level
       ``_resolve_primitive``).  This prevents a second deprecation warning for
       the same artifact when both a top-level and per-slide declaration exist.
    5. Always call ``record_dependency()``; its built-in dedup makes it a no-op
       for primitives already captured.

    Raises:
        GovernanceViolationError: If a DRAFT primitive is encountered and
            ``allow_draft_artifacts`` is ``False``.  Propagates to the caller
            where it is wrapped as a :class:`PipelineError`.
    """
    slides = deck_definition.get("slides")
    if not isinstance(slides, list) or not slides:
        return

    # Primitive IDs already captured through top-level resolution — used to
    # suppress duplicate warnings, not to suppress dependency recording.
    already_governed: set[str] = {
        d.artifact_id
        for d in dependency_chain
        if d.artifact_type == "primitive"
    }

    registry = DesignSystemRegistry(settings.design_system_root)
    seen_in_slides: set[str] = set()

    for slide in slides:
        if not isinstance(slide, dict):
            continue
        raw_primitive = slide.get("primitive")
        if not raw_primitive or not isinstance(raw_primitive, str):
            continue
        primitive_id = raw_primitive
        if primitive_id in seen_in_slides:
            continue  # already processed this ID in an earlier slide
        seen_in_slides.add(primitive_id)

        try:
            definition = registry.get_primitive(primitive_id)
        except DesignSystemError:
            # Unknown or malformed primitive — skip governance; render-time
            # normalisation will handle or degrade gracefully.
            continue

        version = definition.version

        if primitive_id not in already_governed:
            # Enforce lifecycle for primitives not yet governed.  Skipped for
            # primitives that were already enforced via _resolve_primitive so
            # that deprecated artifacts produce exactly one warning per run.
            _enforce_with_audit(
                registry, "primitive", primitive_id, version,
                allow_draft=settings.allow_draft_artifacts,
                governance_warnings=governance_warnings,
                telemetry=telemetry if telemetry is not None else GovernanceTelemetryCollector(),
                usage_scope="per_slide",
                resolution_source="explicit",
            )

        gov = registry.get_artifact_governance("primitive", primitive_id, version)
        record_dependency(
            dependency_chain,
            "primitive", primitive_id, version,
            gov.lifecycle_status.value if gov else None,
            "primitive",
        )


# ---------------------------------------------------------------------------
# Phase 10D.5 — Runtime governance audit helpers
#
# Event scope taxonomy (mirrors telemetry.py docstring):
#
#   Runtime events  — emitted here, during pipeline execution:
#       AUDIT_EVENT_DRAFT_OVERRIDE_USED       (see GovernanceTelemetryCollector)
#       AUDIT_EVENT_DEPRECATED_ARTIFACT_USED  (see GovernanceTelemetryCollector)
#
#   Control-plane events — authoring / governance mutations (Phase 10D.6):
#       AUDIT_EVENT_VERSION_CREATED / PROMOTED / DEPRECATED / DEFAULT_CHANGED
#       Emitted by emit_authoring_event() — NOT by _enforce_with_audit.
# ---------------------------------------------------------------------------


def _enforce_with_audit(
    registry: Any,
    artifact_type: str,
    artifact_id: str,
    version: str,
    *,
    allow_draft: bool,
    governance_warnings: list[str],
    telemetry: GovernanceTelemetryCollector,
    usage_scope: str = "dependency",
    resolution_source: str = "explicit",
) -> None:
    """Call enforce_artifact_lifecycle, record a telemetry event, and capture usage.

    Wraps :meth:`~pptgen.design_system.DesignSystemRegistry.enforce_artifact_lifecycle`
    without changing its behaviour.  After each call:

    1. Looks up governance once (used for all subsequent decisions).
    2. Detects the event type (DEPRECATED / DRAFT-override / APPROVED) and
       delegates to the appropriate collector method.
    3. Always calls :meth:`~GovernanceTelemetryCollector.record_artifact_usage`
       with the full governance context captured during this resolution.

    All audit events are recorded with ``run_id=None``; the caller is responsible
    for backfilling ``run_id`` using :func:`_backfill_run_id` before writing.

    Args:
        registry:            Loaded :class:`~pptgen.design_system.DesignSystemRegistry`.
        artifact_type:       Canonical artifact type string.
        artifact_id:         Stable artifact identifier.
        version:             Resolved artifact version string.
        allow_draft:         Matches the current ``allow_draft_artifacts`` setting.
        governance_warnings: Mutable warning list threaded through the pipeline.
        telemetry:           Run-scoped :class:`GovernanceTelemetryCollector`.
        usage_scope:         ``"top_level"``, ``"dependency"``, or ``"per_slide"``.
        resolution_source:   ``"explicit"`` or ``"default"``.

    Raises:
        GovernanceViolationError: Propagated from the underlying enforcement call
            when *allow_draft* is ``False`` and the artifact is DRAFT.
    """
    warnings_before = len(governance_warnings)
    registry.enforce_artifact_lifecycle(
        artifact_type, artifact_id, version,
        allow_draft=allow_draft,
        warnings=governance_warnings,
    )
    # Fetch governance once; reused for event type detection and usage capture.
    gov = registry.get_artifact_governance(artifact_type, artifact_id, version)
    lifecycle_state = gov.lifecycle_status.value if gov else None

    warning_emitted = len(governance_warnings) > warnings_before
    is_draft_override = False

    if warning_emitted:
        reason = gov.deprecation_reason if gov else None
        telemetry.record_deprecated_usage(artifact_type, artifact_id, version, reason)
    elif allow_draft and gov and lifecycle_state == "draft":
        is_draft_override = True
        telemetry.record_draft_override(artifact_type, artifact_id, version)

    # Always record usage for this artifact resolution.
    telemetry.record_artifact_usage(
        artifact_type=artifact_type,
        artifact_family=artifact_id,
        artifact_version=version,
        lifecycle_state=lifecycle_state,
        resolution_source=resolution_source,
        usage_scope=usage_scope,
        warning_emitted=warning_emitted,
        is_draft_override_usage=is_draft_override,
    )


def _backfill_run_id(
    events: list[GovernanceAuditEvent],
    run_id: str,
) -> list[GovernanceAuditEvent]:
    """Return new event instances with *run_id* set.

    :class:`~pptgen.analytics.GovernanceAuditEvent` is frozen, so ``run_id``
    cannot be set in-place.  :func:`dataclasses.replace` constructs a new
    instance for each event with ``run_id`` overridden.

    Args:
        events: Events collected with ``run_id=None`` during resolution.
        run_id: UUID of the current pipeline run.

    Returns:
        New list of events with ``run_id`` populated.  The original list is
        not modified.
    """
    return [_dc_replace(e, run_id=run_id) for e in events]


# ---------------------------------------------------------------------------
# Phase 10D.4/10D.5 — Telemetry output write (non-blocking)
# ---------------------------------------------------------------------------


def _write_telemetry_outputs_nonblocking(result: PipelineResult, settings: Any) -> None:
    """Write all telemetry outputs for *result* to the configured analytics dir.

    Writes are grouped by concern:

    - Audit events     → ``audit_events.jsonl``  (governance runtime events)
    - Run record       → ``run_records.jsonl``   (per-run summary)
    - Usage events     → ``usage_events.jsonl``  (per-artifact usage ledger)
    - Aggregates       → ``usage_aggregates.json`` (mutable aggregate cache)
    - Usage snapshot   → ``governance/usage_runs/<run_id>/artifact_usage_snapshot.json``

    No-op when :attr:`~pptgen.config.RuntimeSettings.analytics_dir` is
    empty (analytics disabled).  Each writer call is independently
    non-blocking — an error in one does not prevent the others from running.

    Args:
        result:   The completed :class:`PipelineResult`.
        settings: :class:`~pptgen.config.RuntimeSettings` providing
                  ``analytics_dir_path``.
    """
    analytics_dir = settings.analytics_dir_path
    if analytics_dir is None:
        return
    if result.run_record is not None:
        write_run_record(result.run_record, analytics_dir)
        # Phase 10D.5 — rebuild daily aggregates from persisted run snapshots.
        # Called AFTER write_usage_snapshot so the new snapshot is included.
        _run_date = result.run_record.timestamp_utc.date()
    else:
        _run_date = None
    write_usage_events(result.usage_events, analytics_dir)
    update_aggregates(result.usage_events, analytics_dir)
    write_audit_events(result.audit_events, analytics_dir)
    write_usage_snapshot(result.usage_records, analytics_dir, result.run_id)
    if _run_date is not None:
        update_daily_aggregates(analytics_dir, _run_date)


def _write_failure_telemetry_nonblocking(
    telemetry: GovernanceTelemetryCollector,
    settings: Any,
    run_id: str,
    run_date: date | None = None,
) -> None:
    """Write failure-path telemetry (usage snapshot + failure attribution + aggregates).

    Called from each resolution-stage except block after
    :meth:`~GovernanceTelemetryCollector.finalize_usage` has run.
    Non-blocking — errors are swallowed by the underlying writer functions.

    No-op when analytics is disabled.

    Args:
        telemetry: Finalized collector for the failed run.
        settings:  :class:`~pptgen.config.RuntimeSettings`.
        run_id:    UUID of the failed run.
        run_date:  UTC date when the run started; used to rebuild daily aggregates.
    """
    analytics_dir = settings.analytics_dir_path
    if analytics_dir is None:
        return
    write_usage_snapshot(telemetry.get_usage_records(), analytics_dir, run_id)
    attribution = telemetry.get_failure_attribution(run_id=run_id, run_failed=True)
    write_failure_attribution(attribution, analytics_dir, run_id)
    if run_date is not None:
        update_daily_aggregates(analytics_dir, run_date)


# ---------------------------------------------------------------------------
# Phase 10D.3 — Usage event builder
# ---------------------------------------------------------------------------


def _build_usage_events(
    dependency_chain: list[ResolvedArtifactDependency],
    run_id: str,
    run_succeeded: bool,
    settings: Any,
) -> list[ArtifactUsageEvent]:
    """Derive one :class:`~pptgen.analytics.ArtifactUsageEvent` per dependency.

    For each :class:`~pptgen.design_system.dependency_models.ResolvedArtifactDependency`
    in *dependency_chain*, looks up the artifact family to determine whether the
    resolved version was the designated default at the time of the run.

    The design system registry is instantiated once per call and only when
    *dependency_chain* is non-empty — it is never loaded for plain runs that
    use no governed artifacts.

    ``was_default`` is ``True`` only when the dependency carries a non-``None``
    version **and** that version matches the family's ``default_version`` pointer.
    Any exception from the family lookup (e.g. unrecognised artifact type) is
    silently suppressed — ``was_default`` falls back to ``False`` so that
    analytics capture never blocks a pipeline return.

    Args:
        dependency_chain: Resolved artifacts from the current run.
        run_id:           UUID of the current run.
        run_succeeded:    ``True`` when the run completed without exception.
        settings:         :class:`~pptgen.config.RuntimeSettings` providing
                          ``design_system_root``.

    Returns:
        List of :class:`~pptgen.analytics.ArtifactUsageEvent` in the same
        order as *dependency_chain*.  Empty when *dependency_chain* is empty.
    """
    if not dependency_chain:
        return []

    registry = DesignSystemRegistry(settings.design_system_root)
    events: list[ArtifactUsageEvent] = []

    for dep in dependency_chain:
        was_default = False
        if dep.version is not None:
            try:
                family = registry.get_artifact_family(dep.artifact_type, dep.artifact_id)
                was_default = (
                    family is not None and family.default_version == dep.version
                )
            except Exception:
                was_default = False  # never block analytics capture

        events.append(ArtifactUsageEvent(
            run_id=run_id,
            artifact_type=dep.artifact_type,
            artifact_id=dep.artifact_id,
            version=dep.version,
            lifecycle_status=dep.lifecycle_status,
            was_default=was_default,
            run_succeeded=run_succeeded,
        ))

    return events


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

_CI_INTERNAL_SLIDE_KEYS = frozenset({"_ci_metadata"})


def _strip_ci_slide_internals(deck_definition: dict[str, Any]) -> dict[str, Any]:
    """Remove CI-internal keys from slide dicts before rendering.

    ``_ci_metadata`` is carried in the stored deck_definition for
    observability but is rejected by ``BulletsSlide`` (``extra='forbid'``).
    This helper strips those keys so ``parse_deck()`` succeeds.
    """
    slides = deck_definition.get("slides")
    if not isinstance(slides, list):
        return deck_definition
    if not any(
        isinstance(s, dict) and _CI_INTERNAL_SLIDE_KEYS.intersection(s)
        for s in slides
    ):
        return deck_definition  # fast path — no CI slides present
    cleaned = [
        {k: v for k, v in s.items() if k not in _CI_INTERNAL_SLIDE_KEYS}
        if isinstance(s, dict) else s
        for s in slides
    ]
    return {**deck_definition, "slides": cleaned}


def _render(
    deck_definition: dict[str, Any],
    spec_template: str,
    output_path: Path,
) -> None:
    """Load *deck_definition*, resolve template, and write a .pptx."""
    try:
        stripped = _strip_ci_slide_internals(deck_definition)
        normalized = _normalize_primitive_slides(stripped)
        deck = parse_deck(normalized)
        registry = TemplateRegistry.from_file(_REGISTRY_PATH)
        entry = registry.get(spec_template)
        template_path = _REGISTRY_PATH.parent.parent / entry.path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_deck(deck, template_path, output_path)
    except _PptgenError as exc:
        raise PipelineError(str(exc)) from exc
