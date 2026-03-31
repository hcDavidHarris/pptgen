"""API request and response schemas.

All models use Pydantic v2 conventions consistent with the rest of the repo.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, UUID4


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TranscriptPayload(BaseModel):
    """Transcript payload for the transcript-ingestion path.

    Attributes:
        title:    Human-readable label for the meeting or recording.
        content:  Raw transcript text.  Must be non-empty.
        metadata: Optional meeting context — meeting_type, meeting_date,
                  participants, speaker_map, tags, etc.
                  ``meeting_type`` of ``"eos"``, ``"l10"``, ``"rocks"``, or
                  ``"quarterly"`` will produce an EOSRocksBrief; all others
                  default to StrategicBrief.
    """

    title: str = Field(..., description="Human-readable label for the meeting or recording.")
    content: str = Field(..., description="Raw transcript text.  Must be non-empty.")
    metadata: dict | None = Field(
        None,
        description=(
            "Optional meeting context.  Recognised keys: meeting_type, meeting_date, "
            "participants, speaker_map, tags."
        ),
    )


class GenerateRequest(BaseModel):
    """Request body for ``POST /generate``.

    Mode detection priority (server-side):
        1. ``transcript_payload`` → transcript ingestion path
        2. ``content_intent`` → content-intelligence path
        3. ``text`` → raw text / playbook path

    Attributes:
        text:               Raw input text to process through the pipeline.
                            Must be an empty string when ``transcript_payload``
                            or ``content_intent`` is provided.
        mode:               Execution mode — ``"deterministic"`` (default) or ``"ai"``.
        template_id:        Optional template override.  Must be a registered ID.
        artifacts:          If ``True``, export pipeline artifacts alongside the deck.
        preview_only:       If ``True``, plan the deck but skip rendering the ``.pptx``.
        content_intent:     Structured content intent for the content-intelligence path.
                            When supplied the CI layer drives deck building and the
                            legacy playbook router is bypassed entirely.
                            Required keys: ``topic`` (str).
                            Optional keys: ``goal`` (str), ``audience`` (str),
                            ``context`` (dict).
        transcript_payload: Transcript payload for the transcript-ingestion path.
                            When supplied, the transcript is ingested via Phase 12B
                            adapters/extractors, converted to a typed brief, then
                            translated into a ContentIntent that feeds the existing
                            CI pipeline.  Takes priority over ``content_intent``.
    """

    text: str = Field(..., description="Raw input text for the pipeline.")
    mode: str = Field("deterministic", description="Execution mode: 'deterministic' or 'ai'.")
    template_id: str | None = Field(None, description="Optional template ID override.")
    artifacts: bool = Field(False, description="Export pipeline artifacts.")
    preview_only: bool = Field(
        False,
        description="Plan the deck without rendering a .pptx file.",
    )
    content_intent: dict | None = Field(
        None,
        description=(
            "Structured content intent.  When present the content-intelligence path "
            "drives deck generation.  Must contain at minimum a 'topic' key."
        ),
    )
    transcript_payload: TranscriptPayload | None = Field(
        None,
        description=(
            "Transcript payload for the transcript-ingestion path.  "
            "When present, takes priority over content_intent.  "
            "Must contain non-empty 'title' and 'content'."
        ),
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
    run_id: str | None = Field(None, description="Unique identifier for the pipeline run.")
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
    content_intent_mode: bool = Field(
        False,
        description=(
            "True when the content-intelligence path drove deck generation "
            "(playbook_id will be 'content-intelligence')."
        ),
    )
    transcript_mode: bool = Field(
        False,
        description=(
            "True when the transcript-ingestion path drove deck generation "
            "(playbook_id will be 'transcript-intelligence')."
        ),
    )


class ErrorResponse(BaseModel):
    """Standard error response body."""

    request_id: str = Field(..., description="Unique identifier for this request.")
    error: str = Field(..., description="Human-readable error description.")


# ---------------------------------------------------------------------------
# Job schemas (Stage 6B)
# ---------------------------------------------------------------------------

class JobSubmitRequest(BaseModel):
    """Request body for ``POST /v1/jobs``."""

    input_text: str = Field(..., min_length=1, description="Raw input text for the pipeline.")
    template_id: str | None = Field(None, description="Optional template ID override.")
    mode: str = Field("deterministic", description="Execution mode: 'deterministic' or 'ai'.")
    artifacts: bool = Field(False, description="Export pipeline artifacts.")
    workload_type: str = Field("interactive", description="'interactive' or 'batch'.")


class JobStatusResponse(BaseModel):
    """Response for ``POST /v1/jobs`` (202) and ``GET /v1/jobs/{job_id}``."""

    job_id: str
    run_id: str
    status: str
    workload_type: str
    submitted_at: str
    started_at: str | None = None
    completed_at: str | None = None
    retry_count: int = 0
    error_category: str | None = None
    error_message: str | None = None
    output_path: str | None = None
    playbook_id: str | None = None
    action_type: str | None = None
    source_run_id: str | None = None


class JobListResponse(BaseModel):
    """Response for ``GET /v1/jobs``."""

    jobs: list[JobStatusResponse]
    total: int
    limit: int
    offset: int


class JobCancelResponse(BaseModel):
    """Response for ``POST /v1/jobs/{job_id}/cancel``."""

    job_id: str
    accepted: bool
    status: str
    message: str


class RunActionResponse(BaseModel):
    """Response for POST /v1/runs/{run_id}/retry and /rerun."""

    run_id: str           # new run that was created
    source_run_id: str    # original run this was derived from
    action_type: str      # 'retry' | 'rerun'
    job_id: str | None = None


# ---------------------------------------------------------------------------
# Run and Artifact schemas (Stage 6C)
# ---------------------------------------------------------------------------

class RunResponse(BaseModel):
    """Response for ``GET /v1/runs/{run_id}``."""

    run_id: str
    status: str
    source: str
    job_id: str | None = None
    request_id: str | None = None
    mode: str
    template_id: str | None = None
    playbook_id: str | None = None
    profile: str
    started_at: str
    completed_at: str | None = None
    total_ms: float | None = None
    error_category: str | None = None
    error_message: str | None = None
    manifest_path: str | None = None
    retry_count: int | None = None
    replay_available: bool = False
    action_type: str | None = None
    source_run_id: str | None = None
    template_version: str | None = None
    template_revision_hash: str | None = None


class ArtifactMetadataResponse(BaseModel):
    """Metadata response for a single artifact."""

    artifact_id: str
    run_id: str
    artifact_type: str
    filename: str
    relative_path: str
    mime_type: str
    size_bytes: int
    checksum: str
    is_final_output: bool
    visibility: str
    retention_class: str
    status: str
    created_at: str


# ---------------------------------------------------------------------------
# Observability schemas (Stage 6D)
# ---------------------------------------------------------------------------

class RunListItemResponse(BaseModel):
    """Summary item in a run list response."""

    run_id: str
    status: str
    source: str
    job_id: str | None = None
    started_at: str
    completed_at: str | None = None
    total_ms: float | None = None
    artifact_count: int | None = None
    error_category: str | None = None
    mode: str = "deterministic"
    template_id: str | None = None
    playbook_id: str | None = None


class RunListResponse(BaseModel):
    """Response for ``GET /v1/runs``."""

    runs: list[RunListItemResponse]
    total: int
    limit: int
    offset: int


class RunMetricsResponse(BaseModel):
    """Response for ``GET /v1/runs/{run_id}/metrics``."""

    run_id: str
    total_ms: float | None = None
    artifact_count: int | None = None
    stage_timings: list[dict] = []
    slowest_stage: str | None = None
    fastest_stage: str | None = None


class RunStatsResponse(BaseModel):
    """Response for ``GET /v1/runs/stats``."""

    window_hours: int
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    running_runs: int
    success_rate: float | None = None   # None when total_runs == 0
    avg_duration_ms: float | None = None


class SystemHealthResponse(BaseModel):
    """Response for ``GET /v1/system/health``."""

    status: str                   # 'healthy' | 'degraded'
    queued_jobs: int
    running_jobs: int
    failed_jobs_1h: int
    run_store_ok: bool
    job_store_ok: bool


# ---------------------------------------------------------------------------
# Template Registry schemas (Phase 8 Stage 1 + Stage 2)
# ---------------------------------------------------------------------------

class TemplateVersionResponse(BaseModel):
    """A single immutable version of a registered template."""

    version: str
    template_revision_hash: str
    template_path: str | None = None
    playbook_path: str | None = None
    input_contract_version: str | None = None
    ai_mode: str = "optional"


class TemplateDetailResponse(BaseModel):
    """Response for ``GET /v1/templates/{template_id}``."""

    template_id: str
    name: str
    description: str | None = None
    owner: str | None = None
    lifecycle_status: str
    versions: list[str]  # ordered list of version strings (ascending semver)


# ---------------------------------------------------------------------------
# Governance schemas (Phase 8 Stage 3)
# ---------------------------------------------------------------------------

class PromoteVersionRequest(BaseModel):
    """Body for ``POST /v1/templates/{id}/versions/{version}/promote``."""
    reason: str | None = None
    actor: str | None = None


class DeprecateVersionRequest(BaseModel):
    """Body for ``POST /v1/templates/{id}/versions/{version}/deprecate``."""
    reason: str
    actor: str | None = None


class LifecycleChangeRequest(BaseModel):
    """Body for ``POST /v1/templates/{id}/lifecycle``."""
    lifecycle_status: str
    reason: str | None = None
    actor: str | None = None


class GovernanceActionResponse(BaseModel):
    """Response for promote / deprecate / lifecycle-change actions."""
    template_id: str
    version: str | None = None
    action: str
    accepted: bool
    message: str
    previous_default: str | None = None     # set on promote


class GovernanceStateResponse(BaseModel):
    """Response for ``GET /v1/templates/{id}/governance``."""
    template_id: str
    lifecycle_status: str                    # effective lifecycle
    default_version: str | None = None
    deprecated_versions: list[str] = []


class GovernanceAuditEvent(BaseModel):
    """A single audit trail entry."""
    event_type: str
    template_id: str
    template_version: str | None = None
    actor: str | None = None
    reason: str | None = None
    timestamp: str
    metadata: dict | None = None


# Extended version info with governance overlay
class TemplateVersionWithGovernance(BaseModel):
    """Version info including governance state, for operator UI."""
    version: str
    template_revision_hash: str
    template_path: str | None = None
    playbook_path: str | None = None
    input_contract_version: str | None = None
    ai_mode: str = "optional"
    is_default: bool = False
    deprecated_at: str | None = None
    deprecation_reason: str | None = None
    promotion_timestamp: str | None = None


class TemplateRunItem(BaseModel):
    """A single run entry in a template runs response."""

    run_id: str
    status: str
    template_version: str | None = None
    template_revision_hash: str | None = None
    started_at: str
    completed_at: str | None = None
    total_ms: float | None = None
    artifact_count: int | None = None
    error_category: str | None = None
    mode: str = "deterministic"
    playbook_id: str | None = None


class TemplateRunsResponse(BaseModel):
    """Response for ``GET /v1/templates/{template_id}/runs``."""

    template_id: str
    runs: list[TemplateRunItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Template Usage Analytics schemas (Phase 8 Analytics)
# ---------------------------------------------------------------------------

class TemplateUsageSummaryResponse(BaseModel):
    """Response for ``GET /v1/templates/{template_id}/analytics/summary``."""

    template_id: str
    date_window_days: int
    total_runs: int
    completed_runs: int
    failed_runs: int
    cancelled_runs: int
    failure_rate: float | None = None   # None when total_runs == 0


class TemplateVersionUsageItem(BaseModel):
    """Per-version analytics row."""

    template_version: str
    total_runs: int
    failed_runs: int
    failure_rate: float | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None


class TemplateVersionUsageResponse(BaseModel):
    """Response for ``GET /v1/templates/{template_id}/analytics/versions``."""

    template_id: str
    date_window_days: int
    versions: list[TemplateVersionUsageItem]


class TemplateUsageTrendItem(BaseModel):
    """One data point in the daily adoption trend."""

    date: str
    template_version: str
    run_count: int


class TemplateUsageTrendResponse(BaseModel):
    """Response for ``GET /v1/templates/{template_id}/analytics/trend``."""

    template_id: str
    date_window_days: int
    trend: list[TemplateUsageTrendItem]
