"""API request and response schemas.

All models use Pydantic v2 conventions consistent with the rest of the repo.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, UUID4


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    """Request body for ``POST /generate``.

    Attributes:
        text:         Raw input text to process through the pipeline.
        mode:         Execution mode — ``"deterministic"`` (default) or ``"ai"``.
        template_id:  Optional template override.  Must be a registered ID.
        artifacts:    If ``True``, export pipeline artifacts alongside the deck.
        preview_only: If ``True``, plan the deck but skip rendering the ``.pptx``.
    """

    text: str = Field(..., description="Raw input text for the pipeline.")
    mode: str = Field("deterministic", description="Execution mode: 'deterministic' or 'ai'.")
    template_id: str | None = Field(None, description="Optional template ID override.")
    artifacts: bool = Field(False, description="Export pipeline artifacts.")
    preview_only: bool = Field(
        False,
        description="Plan the deck without rendering a .pptx file.",
    )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Response for ``GET /health``."""

    request_id: str = Field(..., description="Unique identifier for this request.")
    status: str = Field(..., description="Service health status.  Normally 'ok'.")


class TemplatesResponse(BaseModel):
    """Response for ``GET /templates``."""

    request_id: str = Field(..., description="Unique identifier for this request.")
    templates: list[str] = Field(..., description="Registered template IDs.")


class PlaybooksResponse(BaseModel):
    """Response for ``GET /playbooks``."""

    request_id: str = Field(..., description="Unique identifier for this request.")
    playbooks: list[str] = Field(..., description="Available playbook IDs.")


class GenerateResponse(BaseModel):
    """Response for ``POST /generate``.

    Attributes:
        request_id:     Unique identifier for this request.
        success:        Whether the pipeline completed without error.
        playbook_id:    Playbook chosen by the input router.
        template_id:    Template ID used (resolved or default).
        mode:           Execution mode that was used.
        stage:          Final pipeline stage reached.
        slide_count:    Number of planned slides, if available.
        slide_types:    Ordered list of slide type strings, if available.
        output_path:    Path to the rendered ``.pptx`` file, or ``None`` for
                        preview-only requests.
        artifact_paths: Mapping of artifact name to file path, or ``None``.
        notes:          Optional diagnostic notes from the pipeline.
    """

    request_id: str = Field(..., description="Unique identifier for this request.")
    success: bool
    playbook_id: str
    template_id: str | None = None
    mode: str
    stage: str
    slide_count: int | None = None
    slide_types: list[str] | None = None
    output_path: str | None = None
    artifact_paths: dict[str, str] | None = None
    notes: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response body."""

    request_id: str = Field(..., description="Unique identifier for this request.")
    error: str = Field(..., description="Human-readable error description.")
