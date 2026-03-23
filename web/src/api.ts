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

import type { GenerateRequest, GenerateResponse, TemplatesResponse } from './types'
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
