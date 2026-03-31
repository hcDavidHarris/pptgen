/**
 * Tests for the API client (api.ts).
 * Uses vi.stubGlobal to replace fetch with a controlled mock.
 * Uses vi.stubEnv to test VITE_API_BASE_URL behaviour.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchTemplates, generate, downloadUrl } from '../api'
import { ApiError } from '../types'

// ── helpers ──────────────────────────────────────────────────────────────────

function mockFetch(body: unknown, status = 200) {
  return vi.fn().mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

function mockFetchError(body: unknown, status: number) {
  return vi.fn().mockResolvedValueOnce({
    ok: false,
    status,
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  vi.unstubAllEnvs()
})

// ── fetchTemplates ────────────────────────────────────────────────────────────

describe('fetchTemplates', () => {
  it('returns the templates array from the response', async () => {
    vi.stubGlobal('fetch', mockFetch({
      request_id: 'abc',
      templates: ['ops_review_v1', 'executive_brief_v1'],
    }))

    const result = await fetchTemplates()
    expect(result).toEqual(['ops_review_v1', 'executive_brief_v1'])
  })

  it('calls GET /v1/templates with no base when VITE_API_BASE_URL is unset', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    const fakeFetch = mockFetch({ request_id: 'abc', templates: [] })
    vi.stubGlobal('fetch', fakeFetch)

    await fetchTemplates()
    expect(fakeFetch).toHaveBeenCalledWith('/v1/templates')
  })

  it('prefixes URL with VITE_API_BASE_URL when set', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    const fakeFetch = mockFetch({ request_id: 'abc', templates: [] })
    vi.stubGlobal('fetch', fakeFetch)

    await fetchTemplates()
    expect(fakeFetch).toHaveBeenCalledWith('http://localhost:8000/v1/templates')
  })

  it('throws ApiError on non-2xx response with string detail', async () => {
    vi.stubGlobal('fetch', mockFetchError({ detail: 'service unavailable' }, 503))
    await expect(fetchTemplates()).rejects.toBeInstanceOf(ApiError)
  })

  it('includes statusCode on non-2xx response', async () => {
    vi.stubGlobal('fetch', mockFetchError({ detail: 'service unavailable' }, 503))
    await expect(fetchTemplates()).rejects.toMatchObject({ statusCode: 503 })
  })
})

// ── generate ─────────────────────────────────────────────────────────────────

describe('generate', () => {
  const successResponse = {
    request_id: 'req-001',
    success: true,
    playbook_id: 'meeting-notes-to-eos-rocks',
    template_id: 'ops_review_v1',
    mode: 'deterministic',
    stage: 'rendered',
    slide_count: 4,
    slide_types: ['title', 'bullets', 'bullets', 'closing'],
    output_path: '/tmp/pptgen_api/abc/output.pptx',
    artifact_paths: null,
    notes: null,
  }

  it('returns the generate response on success', async () => {
    vi.stubGlobal('fetch', mockFetch(successResponse))

    const res = await generate({
      text: 'Meeting notes.',
      mode: 'deterministic',
      preview_only: false,
    })

    expect(res.request_id).toBe('req-001')
    expect(res.playbook_id).toBe('meeting-notes-to-eos-rocks')
    expect(res.stage).toBe('rendered')
  })

  it('posts to /v1/generate with JSON body (no base by default)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    const fakeFetch = mockFetch(successResponse)
    vi.stubGlobal('fetch', fakeFetch)

    await generate({ text: 'hello', mode: 'ai', preview_only: true })

    expect(fakeFetch).toHaveBeenCalledWith('/v1/generate', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: expect.stringContaining('"preview_only":true'),
    }))
  })

  it('prefixes /v1/generate with VITE_API_BASE_URL when set', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://api.example.internal')
    const fakeFetch = mockFetch(successResponse)
    vi.stubGlobal('fetch', fakeFetch)

    await generate({ text: 'hello', mode: 'deterministic', preview_only: false })

    expect(fakeFetch).toHaveBeenCalledWith(
      'http://api.example.internal/v1/generate',
      expect.any(Object),
    )
  })

  it('throws ApiError with request_id from error detail object', async () => {
    vi.stubGlobal('fetch', mockFetchError(
      { detail: { error: 'Unknown mode', request_id: 'err-123' } },
      400,
    ))

    try {
      await generate({ text: 'x', mode: 'bad' as never, preview_only: false })
      expect.fail('should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).requestId).toBe('err-123')
      expect((err as ApiError).message).toBe('Unknown mode')
      expect((err as ApiError).statusCode).toBe(400)
    }
  })

  it('throws ApiError with statusCode on plain 422', async () => {
    vi.stubGlobal('fetch', mockFetchError(
      { detail: [{ msg: 'field required', type: 'missing' }] },
      422,
    ))

    await expect(
      generate({ text: 'x', mode: 'deterministic', preview_only: false })
    ).rejects.toMatchObject({ statusCode: 422 })
  })
})

// ── downloadUrl ───────────────────────────────────────────────────────────────

describe('downloadUrl', () => {
  it('builds a relative /v1/files/download URL when no base is set', () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    const url = downloadUrl('/tmp/pptgen_api/abc/output.pptx')
    expect(url).toBe('/v1/files/download?path=%2Ftmp%2Fpptgen_api%2Fabc%2Foutput.pptx')
  })

  it('prefixes download URL with VITE_API_BASE_URL when set', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    const url = downloadUrl('/tmp/pptgen_api/abc/output.pptx')
    expect(url).toContain('http://localhost:8000/v1/files/download')
  })
})
