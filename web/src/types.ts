/** API request and response types — mirrors src/pptgen/api/schemas.py */

// ---------------------------------------------------------------------------
// Run types (Phase 7)
// ---------------------------------------------------------------------------

export type RunStatus = 'running' | 'succeeded' | 'failed' | 'cancelled'
export type RunSource = 'api_sync' | 'api_async' | 'cli' | 'batch'

export interface RunListItem {
  run_id: string
  status: RunStatus
  source: RunSource
  job_id: string | null
  started_at: string
  completed_at: string | null
  total_ms: number | null
  artifact_count: number | null
  error_category: string | null
  mode: string
  template_id: string | null
  playbook_id: string | null
}

export interface RunListResponse {
  runs: RunListItem[]
  total: number
  limit: number
  offset: number
}

export interface FetchRunsParams {
  limit?: number
  offset?: number
  status?: string
  source?: string
  mode?: string
}

// ---------------------------------------------------------------------------
// Run detail types (Phase 7 PR 4)
// ---------------------------------------------------------------------------

export interface RunDetail {
  run_id: string
  status: RunStatus
  source: RunSource
  job_id: string | null
  request_id: string | null
  mode: string
  template_id: string | null
  playbook_id: string | null
  profile: string
  started_at: string
  completed_at: string | null
  total_ms: number | null
  error_category: string | null
  error_message: string | null
  manifest_path: string | null
  retry_count?: number | null
  artifact_count?: number | null
  replay_available?: boolean
  action_type?: string | null
  source_run_id?: string | null
  // Template lineage (Phase 8 Stage 1–2)
  template_version?: string | null
  template_revision_hash?: string | null
}

export interface RunActionResponse {
  run_id: string
  source_run_id: string
  action_type: 'retry' | 'rerun'
  job_id: string | null
}

export interface StageTimer {
  stage: string
  duration_ms: number | null
}

export interface RunMetrics {
  run_id: string
  total_ms: number | null
  artifact_count: number | null
  stage_timings: StageTimer[]
  slowest_stage: string | null
  fastest_stage: string | null
}

// ---------------------------------------------------------------------------
// Artifact types (Phase 7 PR 5)
// ---------------------------------------------------------------------------

export interface ArtifactMetadata {
  artifact_id: string
  run_id: string
  artifact_type: string
  filename: string
  relative_path: string
  mime_type: string
  size_bytes: number
  checksum: string
  is_final_output: boolean
  visibility: 'downloadable' | 'internal'
  retention_class: string
  status: 'present' | 'deleted' | 'expired'
  created_at: string
}

// ---------------------------------------------------------------------------
// Run stats (Phase 7 Stage 2 PR 2)
// ---------------------------------------------------------------------------

export interface RunStats {
  window_hours: number
  total_runs: number
  succeeded_runs: number
  failed_runs: number
  running_runs: number
  success_rate: number | null
  avg_duration_ms: number | null
}

// ---------------------------------------------------------------------------
// Run comparison (Phase 7 Stage 2 PR 3)
// ---------------------------------------------------------------------------

export interface RunCompareData {
  a: RunDetail
  b: RunDetail
}

// ---------------------------------------------------------------------------
// System health (Phase 7 Stage 2 PR 4)
// ---------------------------------------------------------------------------

export interface SystemHealth {
  status: 'healthy' | 'degraded'
  queued_jobs: number
  running_jobs: number
  failed_jobs_1h: number
  run_store_ok: boolean
  job_store_ok: boolean
}

// ---------------------------------------------------------------------------
// Job types (Phase 7 Stage 3)
// ---------------------------------------------------------------------------

export type JobStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'retrying'
  | 'cancelled'
  | 'timed_out'
  | 'cancellation_requested'

export interface JobListItem {
  job_id: string
  run_id: string
  status: JobStatus
  workload_type: string
  submitted_at: string
  started_at: string | null
  completed_at: string | null
  retry_count: number
  error_category: string | null
  error_message: string | null
  output_path: string | null
  playbook_id: string | null
  action_type: string | null
  source_run_id: string | null
}

export interface JobListResponse {
  jobs: JobListItem[]
  total: number
  limit: number
  offset: number
}

export interface FetchJobsParams {
  limit?: number
  offset?: number
  status?: string
}

export interface JobCancelResponse {
  job_id: string
  accepted: boolean
  status: string
  message: string
}

export type ExecutionMode = 'deterministic' | 'ai'

export interface ContentIntentPayload {
  topic: string
  goal?: string
  audience?: string
  context?: Record<string, unknown>
}

/** Transcript payload for the transcript-ingestion path (Phase 12B). */
export interface TranscriptPayload {
  title: string
  content: string
  metadata?: {
    meeting_type?: 'standard' | 'eos' | 'l10' | 'rocks' | string
    meeting_date?: string
    participants?: string[]
    speaker_map?: Record<string, string>
    tags?: string[]
    audience?: string
    [key: string]: unknown
  }
}

export interface GenerateRequest {
  text: string
  mode: ExecutionMode
  template_id?: string
  artifacts?: boolean
  preview_only?: boolean
  content_intent?: ContentIntentPayload
  /** Transcript payload for the transcript-ingestion path. Takes priority
   *  over content_intent when both are present. text must be "" when set. */
  transcript_payload?: TranscriptPayload
}

export interface GenerateResponse {
  request_id: string
  success: boolean
  playbook_id: string
  template_id: string | null
  mode: string
  stage: string
  slide_count: number | null
  slide_types: string[] | null
  output_path: string | null
  artifact_paths: Record<string, string> | null
  notes: string | null
  content_intent_mode?: boolean
  /** True when the transcript-ingestion path drove deck generation.
   *  playbook_id will be "transcript-intelligence". */
  transcript_mode?: boolean
}

export interface HealthResponse {
  request_id: string
  status: string
}

export interface TemplatesResponse {
  request_id: string
  templates: string[]
}

export interface PlaybooksResponse {
  request_id: string
  playbooks: string[]
}

export interface ApiErrorDetail {
  request_id?: string
  error?: string
  detail?: string | { error: string; request_id?: string }
}

// ---------------------------------------------------------------------------
// Template Registry types (Phase 8 Stage 2)
// ---------------------------------------------------------------------------

export interface TemplateVersionDetail {
  version: string
  template_revision_hash: string
  template_path: string | null
  playbook_path: string | null
  input_contract_version: string | null
  ai_mode: string
}

export interface TemplateDetail {
  template_id: string
  name: string
  description: string | null
  owner: string | null
  lifecycle_status: string
  versions: string[]  // ascending semver strings
}

export interface TemplateRunItem {
  run_id: string
  status: string
  template_version: string | null
  template_revision_hash: string | null
  started_at: string
  completed_at: string | null
  total_ms: number | null
  artifact_count: number | null
  error_category: string | null
  mode: string
  playbook_id: string | null
}

export interface TemplateRunsResponse {
  template_id: string
  runs: TemplateRunItem[]
  total: number
  limit: number
  offset: number
}

export interface FetchTemplateRunsParams {
  template_version?: string
  status?: string
  days?: number
  limit?: number
  offset?: number
}

// ---------------------------------------------------------------------------
// Template Governance types (Phase 8 Stage 3)
// ---------------------------------------------------------------------------

export interface TemplateVersionWithGovernance {
  version: string
  template_revision_hash: string
  template_path: string | null
  playbook_path: string | null
  input_contract_version: string | null
  ai_mode: string
  is_default: boolean
  deprecated_at: string | null
  deprecation_reason: string | null
  promotion_timestamp: string | null
}

export interface GovernanceState {
  template_id: string
  lifecycle_status: string
  default_version: string | null
  deprecated_versions: string[]
}

export interface GovernanceAuditEvent {
  event_type: string
  template_id: string
  template_version: string | null
  actor: string | null
  reason: string | null
  timestamp: string
  metadata: Record<string, unknown> | null
}

export interface GovernanceActionResponse {
  template_id: string
  version: string | null
  action: string
  accepted: boolean
  message: string
  previous_default: string | null
}

export interface PromoteVersionRequest {
  reason?: string
  actor?: string
}

export interface DeprecateVersionRequest {
  reason: string
  actor?: string
}

export interface LifecycleChangeRequest {
  lifecycle_status: string
  reason?: string
  actor?: string
}

// ---------------------------------------------------------------------------
// Template Usage Analytics types (Phase 8 Analytics)
// ---------------------------------------------------------------------------

export interface TemplateUsageSummary {
  template_id: string
  date_window_days: number
  total_runs: number
  completed_runs: number
  failed_runs: number
  cancelled_runs: number
  failure_rate: number | null
}

export interface TemplateVersionUsageItem {
  template_version: string
  total_runs: number
  failed_runs: number
  failure_rate: number | null
  first_seen_at: string | null
  last_seen_at: string | null
}

export interface TemplateVersionUsageResponse {
  template_id: string
  date_window_days: number
  versions: TemplateVersionUsageItem[]
}

export interface TemplateUsageTrendItem {
  date: string
  template_version: string
  run_count: number
}

export interface TemplateUsageTrendResponse {
  template_id: string
  date_window_days: number
  trend: TemplateUsageTrendItem[]
}

/** Structured error thrown by the API client. */
export class ApiError extends Error {
  readonly requestId: string | null
  readonly statusCode: number

  constructor(message: string, statusCode: number, requestId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.requestId = requestId
  }
}
