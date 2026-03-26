/**
 * pptgen API client.
 *
 * All calls go through the existing /v1 endpoints.
 *
 * Base URL is read from the VITE_API_BASE_URL environment variable.
 * Leave it unset (or empty) to use the Vite dev-server proxy / same-origin
 * behaviour.  Set it to an explicit origin for container or reverse-proxy
 * deployments:
 *
 *   VITE_API_BASE_URL=http://api.example.internal
 *
 * The variable is read lazily so the test suite can stub it per-test.
 */

import type { ArtifactMetadata, FetchJobsParams, FetchRunsParams, FetchTemplateRunsParams, GenerateRequest, GenerateResponse, JobCancelResponse, JobListResponse, RunActionResponse, RunCompareData, RunDetail, RunListResponse, RunMetrics, RunStats, SystemHealth, TemplateDetail, TemplateRunsResponse, TemplatesResponse, TemplateVersionDetail } from './types'
import { ApiError } from './types'

/** Returns the configured API base (no trailing slash). */
function getApiBase(): string {
  return (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''
}

/** Extract a useful error message and optional request_id from a non-2xx response. */
async function parseErrorResponse(res: Response): Promise<ApiError> {
  let message = `HTTP ${res.status}`
  let requestId: string | null = null

  try {
    const body = await res.json()
    const detail = body?.detail
    if (typeof detail === 'string') {
      message = detail
    } else if (detail && typeof detail === 'object') {
      message = detail.error ?? message
      requestId = detail.request_id ?? null
    } else if (typeof body?.error === 'string') {
      message = body.error
      requestId = body.request_id ?? null
    }
  } catch {
    // body was not JSON — keep the default message
  }

  return new ApiError(message, res.status, requestId)
}

/** Fetch the list of registered template IDs. */
export async function fetchTemplates(): Promise<string[]> {
  const res = await fetch(`${getApiBase()}/v1/templates`)
  if (!res.ok) throw await parseErrorResponse(res)
  const data: TemplatesResponse = await res.json()
  return data.templates
}

/** Run the generation pipeline (preview or full). */
export async function generate(request: GenerateRequest): Promise<GenerateResponse> {
  const res = await fetch(`${getApiBase()}/v1/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Build a download URL for a generated file. */
export function downloadUrl(outputPath: string): string {
  return `${getApiBase()}/v1/files/download?path=${encodeURIComponent(outputPath)}`
}

/** Fetch a single run by ID. */
export async function fetchRun(runId: string): Promise<RunDetail> {
  const res = await fetch(`${getApiBase()}/v1/runs/${encodeURIComponent(runId)}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Fetch stage timing metrics for a run. */
export async function fetchRunMetrics(runId: string): Promise<RunMetrics> {
  const res = await fetch(`${getApiBase()}/v1/runs/${encodeURIComponent(runId)}/metrics`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Fetch artifacts for a run. */
export async function fetchRunArtifacts(runId: string): Promise<ArtifactMetadata[]> {
  const res = await fetch(`${getApiBase()}/v1/runs/${encodeURIComponent(runId)}/artifacts`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Fetch the manifest JSON for a run. */
export async function fetchRunManifest(runId: string): Promise<unknown> {
  const res = await fetch(`${getApiBase()}/v1/runs/${encodeURIComponent(runId)}/manifest`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Build a download URL for an artifact by its artifact_id. */
export function artifactDownloadUrl(artifactId: string): string {
  return `${getApiBase()}/v1/artifacts/${encodeURIComponent(artifactId)}/download`
}

/** Fetch paginated run list with optional filters. */
export async function fetchRuns(params: FetchRunsParams = {}): Promise<RunListResponse> {
  const qs = new URLSearchParams()
  if (params.limit != null) qs.set('limit', String(params.limit))
  if (params.offset != null) qs.set('offset', String(params.offset))
  if (params.status) qs.set('status', params.status)
  if (params.source) qs.set('source', params.source)
  if (params.mode) qs.set('mode', params.mode)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  const res = await fetch(`${getApiBase()}/v1/runs${query}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}


/** Fetch aggregate run statistics for a time window (default 24h). */
export async function fetchRunStats(window = '24h'): Promise<RunStats> {
  const res = await fetch(`${getApiBase()}/v1/runs/stats?window=${encodeURIComponent(window)}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Fetch two runs in parallel for side-by-side comparison. */
export async function fetchRunPair(idA: string, idB: string): Promise<RunCompareData> {
  const [a, b] = await Promise.all([fetchRun(idA), fetchRun(idB)])
  return { a, b }
}

/** Fetch system health snapshot. */
export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await fetch(`${getApiBase()}/v1/system/health`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Retry a failed run — creates a new run and job. */
export async function retryRun(runId: string): Promise<RunActionResponse> {
  const res = await fetch(`${getApiBase()}/v1/runs/${encodeURIComponent(runId)}/retry`, {
    method: 'POST',
  })
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Rerun any run regardless of status. */
export async function rerunRun(runId: string): Promise<RunActionResponse> {
  const res = await fetch(`${getApiBase()}/v1/runs/${encodeURIComponent(runId)}/rerun`, {
    method: 'POST',
  })
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Cancel a job (queued/retrying → cancelled; running → cancellation_requested). */
export async function cancelJob(jobId: string): Promise<JobCancelResponse> {
  const res = await fetch(`${getApiBase()}/v1/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: 'POST',
  })
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Fetch paginated job list with optional status filter. */
export async function fetchJobs(params: FetchJobsParams = {}): Promise<JobListResponse> {
  const qs = new URLSearchParams()
  if (params.limit != null) qs.set('limit', String(params.limit))
  if (params.offset != null) qs.set('offset', String(params.offset))
  if (params.status) qs.set('status', params.status)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  const res = await fetch(`${getApiBase()}/v1/jobs${query}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Fetch template metadata and version list for a single template. */
export async function fetchTemplateDetail(templateId: string): Promise<TemplateDetail> {
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Fetch full version objects (with hash, paths) for a template. */
export async function fetchTemplateVersions(templateId: string): Promise<TemplateVersionDetail[]> {
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/versions`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

/** Fetch runs that used a specific template, with optional filters. */
export async function fetchTemplateRuns(
  templateId: string,
  params: FetchTemplateRunsParams = {},
): Promise<TemplateRunsResponse> {
  const qs = new URLSearchParams()
  if (params.template_version) qs.set('template_version', params.template_version)
  if (params.status) qs.set('status', params.status)
  if (params.days != null) qs.set('days', String(params.days))
  if (params.limit != null) qs.set('limit', String(params.limit))
  if (params.offset != null) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/runs${query}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

// ---------------------------------------------------------------------------
// Template Governance (Phase 8 Stage 3)
// ---------------------------------------------------------------------------

export async function fetchTemplateVersionsWithGovernance(templateId: string): Promise<import('./types').TemplateVersionWithGovernance[]> {
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/versions`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

export async function fetchGovernanceState(templateId: string): Promise<import('./types').GovernanceState> {
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/governance`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

export async function fetchGovernanceAudit(templateId: string, limit = 100): Promise<import('./types').GovernanceAuditEvent[]> {
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/governance/audit?limit=${limit}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

export async function promoteVersion(
  templateId: string,
  version: string,
  body: import('./types').PromoteVersionRequest,
): Promise<import('./types').GovernanceActionResponse> {
  const res = await fetch(
    `${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/versions/${encodeURIComponent(version)}/promote`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
  )
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

export async function deprecateVersion(
  templateId: string,
  version: string,
  body: import('./types').DeprecateVersionRequest,
): Promise<import('./types').GovernanceActionResponse> {
  const res = await fetch(
    `${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/versions/${encodeURIComponent(version)}/deprecate`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
  )
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

// ---------------------------------------------------------------------------
// Template Usage Analytics (Phase 8 Analytics)
// ---------------------------------------------------------------------------

export async function fetchTemplateAnalyticsSummary(
  templateId: string,
  days = 30,
): Promise<import('./types').TemplateUsageSummary> {
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/analytics/summary?days=${days}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

export async function fetchTemplateAnalyticsVersions(
  templateId: string,
  days = 30,
): Promise<import('./types').TemplateVersionUsageResponse> {
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/analytics/versions?days=${days}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

export async function fetchTemplateAnalyticsTrend(
  templateId: string,
  days = 30,
): Promise<import('./types').TemplateUsageTrendResponse> {
  const res = await fetch(`${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/analytics/trend?days=${days}`)
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}

export async function changeLifecycle(
  templateId: string,
  body: import('./types').LifecycleChangeRequest,
): Promise<import('./types').GovernanceActionResponse> {
  const res = await fetch(
    `${getApiBase()}/v1/templates/${encodeURIComponent(templateId)}/lifecycle`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
  )
  if (!res.ok) throw await parseErrorResponse(res)
  return res.json()
}
