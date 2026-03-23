/** API request and response types — mirrors src/pptgen/api/schemas.py */

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
