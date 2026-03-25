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

export type ExecutionMode = 'deterministic' | 'ai'

export interface GenerateRequest {
  text: string
  mode: ExecutionMode
  template_id?: string
  artifacts?: boolean
  preview_only?: boolean
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
