import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { App } from '../App'

const TEMPLATES_RESPONSE = {
  request_id: 'tpl-001',
  templates: ['ops_review_v1', 'architecture_overview_v1'],
}

function ok(body: unknown) {
  return { ok: true, status: 200, body }
}

function makeFetchQueue(...responses: Array<{ ok: boolean; status: number; body: unknown }>) {
  let index = 0
  return vi.fn().mockImplementation(() => {
    const r = responses[index] ?? responses[responses.length - 1]
    index++
    return Promise.resolve({
      ok: r.ok,
      status: r.status,
      json: () => Promise.resolve(r.body),
    })
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('App — layout shell', () => {
  it('renders the page heading', () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    render(<MemoryRouter><App /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'pptgen' })).toBeInTheDocument()
  })

  it('renders Generate nav link', () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    render(<MemoryRouter><App /></MemoryRouter>)
    expect(screen.getByRole('link', { name: 'Generate' })).toBeInTheDocument()
  })

  it('renders Runs nav link', () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    render(<MemoryRouter><App /></MemoryRouter>)
    expect(screen.getByRole('link', { name: 'Runs' })).toBeInTheDocument()
  })

  it('renders GeneratePage at root route', () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    render(<MemoryRouter initialEntries={['/']}><App /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Input' })).toBeInTheDocument()
  })

  it('renders RunsPage at /runs route', () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    render(<MemoryRouter initialEntries={['/runs']}><App /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Runs' })).toBeInTheDocument()
  })

  it('renders RunDetailPage at /runs/:runId route', async () => {
    const RUN = {
      run_id: 'run-abc-123', status: 'succeeded', source: 'api_sync',
      job_id: null, request_id: null, mode: 'deterministic',
      template_id: null, playbook_id: null, profile: 'dev',
      started_at: '2026-03-24T10:00:00.000Z', completed_at: null,
      total_ms: null, error_category: null, error_message: null, manifest_path: null,
    }
    const METRICS = { run_id: 'run-abc-123', total_ms: null, artifact_count: null, stage_timings: [], slowest_stage: null, fastest_stage: null }
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN), ok(METRICS), ok([])))
    render(<MemoryRouter initialEntries={['/runs/run-abc-123']}><App /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Run Detail' })).toBeInTheDocument()
    })
    expect(screen.getByText('run-abc-123')).toBeInTheDocument()
  })
})
