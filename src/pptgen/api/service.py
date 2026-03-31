"""API service helpers.

Thin wrappers around existing pptgen modules so routes.py stays focused on
HTTP concerns.  No new business logic lives here — every call ultimately
delegates to an existing module.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..config import get_settings
from ..content_intelligence import ContentIntent
from ..pipeline import PipelineError, PipelineResult, generate_presentation
from ..playbook_engine.execution_strategy import VALID_STRATEGIES
from ..registry.registry import TemplateRegistry
from ..input_router.routing_table_loader import load_routing_table
from ..runtime import RunContext
from ..runtime.workspace import WorkspaceManager


_REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "registry.yaml"

# Optional artifact services — set from server.py lifespan after Stage 6C stores are ready.
_promoter = None
_run_store = None


def set_artifact_services(promoter, run_store) -> None:
    """Wire in artifact promotion services (called from server.py lifespan)."""
    global _promoter, _run_store
    _promoter = promoter
    _run_store = run_store


def _generate_request_id() -> str:
    """Return a new UUID4 string for per-request tracing."""
    return str(uuid.uuid4())


class APIError(Exception):
    """Raised by service helpers to signal a 4xx-level client error."""

    from pptgen.errors import ErrorCategory
    category = ErrorCategory.VALIDATION

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def list_templates() -> list[str]:
    """Return sorted registered template IDs from the registry."""
    registry = TemplateRegistry.from_file(_REGISTRY_PATH)
    return sorted(e.template_id for e in registry.all())


def list_playbooks() -> list[str]:
    """Return sorted playbook IDs from the routing table."""
    entries = load_routing_table()
    return sorted(e.playbook_id for e in entries)


def _parse_content_intent(raw: dict) -> ContentIntent:
    """Parse a request ``content_intent`` dict into a :class:`ContentIntent`.

    Args:
        raw: Dict with at minimum a ``"topic"`` key.

    Returns:
        :class:`ContentIntent` with topic, goal, audience, context populated.

    Raises:
        APIError: If ``"topic"`` is missing, blank, contains newlines, or
                  exceeds 500 characters.  A topic must be a single-line
                  concept (e.g. "Cloud Cost Optimisation") — not a paragraph,
                  document, or multi-line paste.
    """
    topic = raw.get("topic", "")
    if not isinstance(topic, str) or not topic.strip():
        raise APIError(
            "content_intent must include a non-empty 'topic' string.",
            status_code=400,
        )
    topic = topic.strip()
    if "\n" in topic or "\r" in topic:
        raise APIError(
            "content_intent.topic must be a single-line string (no newlines). "
            "Provide a concise presentation topic, not a multi-line document.",
            status_code=400,
        )
    if len(topic) > 500:
        raise APIError(
            f"content_intent.topic must not exceed 500 characters "
            f"({len(topic)} received).  Provide a concise presentation topic.",
            status_code=400,
        )
    return ContentIntent(
        topic=topic,
        goal=raw.get("goal") or None,
        audience=raw.get("audience") or None,
        context=raw.get("context") or None,
    )


def _ingest_transcript(payload: dict) -> ContentIntent:
    """Convert a transcript payload dict into a :class:`ContentIntent`.

    Delegates to the Phase 12B ingestion pipeline:
        TranscriptAdapter → TranscriptExtractor → Brief → CI bridge

    Args:
        payload: Dict with required ``title`` and ``content`` keys, and
                 optional ``source_id`` and ``metadata``.

    Returns:
        :class:`ContentIntent` ready for ``generate_presentation()``.

    Raises:
        APIError: If the payload is missing required fields or they are empty.
    """
    from ..ingestion.adapters.base import AdapterPayloadError
    from ..ingestion.transcript_orchestrator import ingest_transcript_to_content_intent

    try:
        ingestion_intent = ingest_transcript_to_content_intent(payload)
    except AdapterPayloadError as exc:
        raise APIError(str(exc), status_code=400) from exc

    # The ingestion bridge returns a ContentIntent from pptgen.ingestion.ci_bridge.
    # generate_presentation() expects ContentIntent from pptgen.content_intelligence.
    # Both are identical dataclasses (same fields); duck-typing handles the rest.
    # We re-wrap here to ensure the correct class is used when the CI module is live.
    return ContentIntent(
        topic=ingestion_intent.topic,
        goal=ingestion_intent.goal,
        audience=ingestion_intent.audience,
        context=ingestion_intent.context,
    )


def run_generate(
    text: str,
    mode: str,
    template_id: str | None,
    artifacts: bool,
    preview_only: bool,
    request_id: str | None = None,
    content_intent: dict | None = None,
    transcript_payload: dict | None = None,
) -> tuple[PipelineResult, RunContext]:
    """Validate inputs, run the generation pipeline, and return run metadata.

    Mode detection priority:
        1. ``transcript_payload`` — transcript ingestion path (Phase 12B)
        2. ``content_intent``     — direct content-intelligence path
        3. neither                — raw text / playbook path

    Args:
        text:               Raw input text.
        mode:               Execution mode string.
        template_id:        Optional template ID override.
        artifacts:          Whether to export pipeline artifacts.
        preview_only:       Skip rendering if ``True``.
        request_id:         HTTP request identifier for the :class:`RunContext`.
        content_intent:     Optional structured content intent dict.
        transcript_payload: Optional transcript payload dict.  When present,
                            ingested via Phase 12B pipeline and converted to a
                            ContentIntent that feeds the CI layer.  Takes
                            priority over ``content_intent``.

    Returns:
        A tuple of (:class:`~pptgen.pipeline.PipelineResult`,
        :class:`~pptgen.runtime.RunContext`).

    Raises:
        APIError: For invalid *mode*, malformed *content_intent*, or invalid
                  *transcript_payload* (missing/empty title or content).
        PipelineError: Propagated from the pipeline for other failures.
    """
    if mode not in VALID_STRATEGIES:
        raise APIError(
            f"Unknown mode '{mode}'.  Valid modes: {', '.join(sorted(VALID_STRATEGIES))}.",
            status_code=400,
        )

    # Priority 1 — transcript ingestion path (Phase 12B).
    # Convert transcript payload → typed brief → ContentIntent via ingestion layer.
    parsed_intent: ContentIntent | None = None
    if transcript_payload is not None:
        parsed_intent = _ingest_transcript(transcript_payload)
    # Priority 2 — direct content-intelligence path.
    elif content_intent is not None:
        parsed_intent = _parse_content_intent(content_intent)

    settings = get_settings()
    ctx = RunContext(
        request_id=request_id,
        profile=settings.profile.value,
        mode=mode,
        template_id=template_id,
        config_fingerprint=settings.fingerprint,
    )

    # Resolve workspace and output path — None for preview-only requests.
    output_path: Path | None = None
    ws = None
    if not preview_only:
        mgr = WorkspaceManager.from_settings(settings)
        ws = mgr.create(ctx.run_id)
        ctx.workspace_path = str(ws.root)
        output_path = ws.output_path

    # Artifact directory alongside the workspace output when requested.
    artifacts_dir: Path | None = None
    if artifacts and output_path is not None:
        artifacts_dir = output_path.parent / "artifacts"

    result = generate_presentation(
        text,
        output_path=output_path,
        template_id=template_id,
        mode=mode,
        artifacts_dir=artifacts_dir,
        run_context=ctx,
        content_intent=parsed_intent,
    )

    # Promote artifacts to durable store when services are wired in (Stage 6C).
    if _promoter is not None and _run_store is not None and not preview_only and ws is not None:
        try:
            from ..runs.models import RunRecord, RunSource
            run_rec = RunRecord.create(
                source=RunSource.API_SYNC,
                run_id=ctx.run_id,
                request_id=request_id,
                mode=mode,
                template_id=template_id,
                input_text=text,
            )
            _run_store.create(run_rec)
            _promoter.promote(
                run=run_rec,
                workspace_root=ws.root,
                artifacts_subdir=ws.root / "artifacts",
                run_context_dict=ctx.as_dict(),
                total_ms=ctx.total_ms(),
            )
        except Exception as exc:  # promotion is non-fatal
            import logging
            logging.getLogger(__name__).warning(
                "Artifact promotion failed for run %s: %s", ctx.run_id, exc
            )

    return result, ctx
