"""FastAPI route definitions.

All routes delegate to :mod:`pptgen.api.service`; no pipeline logic lives
here.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..pipeline import PipelineError
from .schemas import (
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    PlaybooksResponse,
    TemplatesResponse,
)
from .service import APIError, _generate_request_id, list_playbooks, list_templates, run_generate

router = APIRouter(prefix="/v1")


@router.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Return a simple health-check response."""
    return HealthResponse(request_id=_generate_request_id(), status="ok")


@router.get("/templates", response_model=TemplatesResponse, tags=["meta"])
def templates() -> TemplatesResponse:
    """Return all registered template IDs."""
    return TemplatesResponse(request_id=_generate_request_id(), templates=list_templates())


@router.get("/playbooks", response_model=PlaybooksResponse, tags=["meta"])
def playbooks() -> PlaybooksResponse:
    """Return all available playbook IDs from the routing table."""
    return PlaybooksResponse(request_id=_generate_request_id(), playbooks=list_playbooks())


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    tags=["generation"],
)
def generate(request: GenerateRequest) -> GenerateResponse:
    """Run the pptgen pipeline and return a structured result.

    Set ``preview_only=true`` to plan the deck without rendering a ``.pptx``.
    Set ``artifacts=true`` to export ``spec.json``, ``slide_plan.json``, and
    ``deck_definition.json`` alongside the rendered file.
    """
    request_id = _generate_request_id()
    is_transcript = request.transcript_payload is not None
    try:
        result, ctx = run_generate(
            text=request.text,
            mode=request.mode,
            template_id=request.template_id,
            artifacts=request.artifacts,
            preview_only=request.preview_only,
            request_id=request_id,
            content_intent=request.content_intent,
            transcript_payload=(
                request.transcript_payload.model_dump() if is_transcript else None
            ),
        )
    except APIError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": str(exc), "request_id": request_id},
        ) from exc
    except PipelineError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "request_id": request_id},
        ) from exc

    slide_count: int | None = None
    slide_types: list[str] | None = None
    if result.slide_plan is not None:
        slide_count = result.slide_plan.slide_count
        slide_types = result.slide_plan.planned_slide_types
    elif result.deck_definition:
        # CI / transcript path: slide_plan is None; derive counts from built deck
        slides = result.deck_definition.get("slides", [])
        slide_count = len(slides)
        slide_types = [s.get("type", "") for s in slides]

    # Transcript path overrides the playbook label so the caller can distinguish it
    # from a raw content-intelligence call without inspecting input fields.
    effective_playbook_id = (
        "transcript-intelligence" if is_transcript else result.playbook_id
    )

    return GenerateResponse(
        request_id=request_id,
        run_id=ctx.run_id,
        success=True,
        playbook_id=effective_playbook_id,
        template_id=result.template_id,
        mode=result.mode,
        stage=result.stage,
        slide_count=slide_count,
        slide_types=slide_types,
        output_path=result.output_path,
        artifact_paths=result.artifact_paths,
        notes=result.notes or None,
        content_intent_mode=(
            False if is_transcript
            else result.playbook_id == "content-intelligence"
        ),
        transcript_mode=is_transcript,
    )
