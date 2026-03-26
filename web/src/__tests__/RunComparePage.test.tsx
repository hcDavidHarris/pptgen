import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { RunComparePage } from '../pages/RunComparePage'

function makeRunDetail(id: string, overrides: Record<string, unknown> = {}) {
  return {
    run_id: id,
    status: 'succeeded',
    source: 'api_sync',
    job_id: null,
    request_id: null,
    mode: 'deterministic',
    template_id: 'hc-default',
    playbook_id: 'meeting-notes',
    profile: 'dev',
    started_at: '2026-03-24T10:00:00.000Z',
    completed_at: '2026-03-24T10:00:02.000Z',
    total_ms: 2000,
    error_category: null,
    error_message: null,
    manifest_path: null,
    retry_count: null,
    artifact_count: 3,
    ...overrides,
  }
}

function makeFetchQueue(responses: Array<{ ok: boolean; status: number; body: unknown }>) {
  let i = 0
  return vi.fn().mockImplementation(() => {
    const r = responses[Math.min(i++, responses.length - 1)]
    return Promise.resolve({
      ok: r.ok,
      status: r.status,
      json: () => Promise.resolve(r.body),
    })
  })
}

function ok(body: unknown) {
  return { ok: true as const, status: 200, body }
}

function renderWithParams(search: string) {
  return render(
    <MemoryRouter initialEntries={[`/runs/compare${search}`]}>
      <RunComparePage />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('RunComparePage — missing params', () => {
  it('shows error when IDs are missing', () => {
    renderWithParams('')
    expect(screen.getByText(/Two run IDs are required/)).toBeInTheDocument()
  })

  it('shows Back to Runs link when params missing', () => {
    renderWithParams('')
    expect(screen.getByRole('link', { name: 'Back to Runs' })).toBeInTheDocument()
  })
})

describe('RunComparePage — successful compare', () => {
  it('renders compare table with both runs', async () => {
    const runA = makeRunDetail('run-aaa-111')
    const runB = makeRunDetail('run-bbb-222')
    vi.stubGlobal('fetch', makeFetchQueue([ok(runA), ok(runB)]))
    renderWithParams('?a=run-aaa-111&b=run-bbb-222')
    await waitFor(() => {
      expect(screen.getByTitle('run-aaa-111')).toBeInTheDocument()
    })
    expect(screen.getByTitle('run-bbb-222')).toBeInTheDocument()
  })

  it('shows field labels in compare table', async () => {
    const runA = makeRunDetail('run-aaa-111')
    const runB = makeRunDetail('run-bbb-222')
    vi.stubGlobal('fetch', makeFetchQueue([ok(runA), ok(runB)]))
    renderWithParams('?a=run-aaa-111&b=run-bbb-222')
    await waitFor(() => screen.getByTitle('run-aaa-111'))
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Mode')).toBeInTheDocument()
    expect(screen.getByText('Duration')).toBeInTheDocument()
  })

  it('highlights differing rows', async () => {
    const runA = makeRunDetail('run-aaa-111', { status: 'succeeded', total_ms: 1000 })
    const runB = makeRunDetail('run-bbb-222', { status: 'failed', total_ms: 2000 })
    vi.stubGlobal('fetch', makeFetchQueue([ok(runA), ok(runB)]))
    const { container } = renderWithParams('?a=run-aaa-111&b=run-bbb-222')
    await waitFor(() => screen.getByTitle('run-aaa-111'))
    expect(container.querySelector('.run-compare__row--diff')).toBeTruthy()
  })

  it('does not highlight rows where values match', async () => {
    const runA = makeRunDetail('run-aaa-111', { mode: 'deterministic' })
    const runB = makeRunDetail('run-bbb-222', { mode: 'deterministic' })
    vi.stubGlobal('fetch', makeFetchQueue([ok(runA), ok(runB)]))
    const { container } = renderWithParams('?a=run-aaa-111&b=run-bbb-222')
    await waitFor(() => screen.getByTitle('run-aaa-111'))
    // Mode row should not have diff class
    const rows = container.querySelectorAll('tr')
    // Find the Mode row
    let modeRowDiff = false
    rows.forEach((row) => {
      if (row.textContent?.includes('Mode') && !row.textContent.includes('Mode\n')) return
      if (row.querySelector('th')?.textContent === 'Mode') {
        modeRowDiff = row.classList.contains('run-compare__row--diff')
      }
    })
    expect(modeRowDiff).toBe(false)
  })

  it('shows Back to Runs link', async () => {
    const runA = makeRunDetail('run-aaa-111')
    const runB = makeRunDetail('run-bbb-222')
    vi.stubGlobal('fetch', makeFetchQueue([ok(runA), ok(runB)]))
    renderWithParams('?a=run-aaa-111&b=run-bbb-222')
    await waitFor(() => screen.getByTitle('run-aaa-111'))
    expect(screen.getByRole('link', { name: 'Back to Runs' })).toBeInTheDocument()
  })
})

describe('RunComparePage — error state', () => {
  it('shows error when fetch fails', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      { ok: false, status: 404, body: { detail: 'Run not found' } },
      { ok: false, status: 404, body: { detail: 'Run not found' } },
    ]))
    renderWithParams('?a=bad-id-1&b=bad-id-2')
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})

describe('RunComparePage — heading', () => {
  it('shows Compare Runs heading', async () => {
    const runA = makeRunDetail('run-aaa-111')
    const runB = makeRunDetail('run-bbb-222')
    vi.stubGlobal('fetch', makeFetchQueue([ok(runA), ok(runB)]))
    renderWithParams('?a=run-aaa-111&b=run-bbb-222')
    expect(screen.getByRole('heading', { name: 'Compare Runs' })).toBeInTheDocument()
  })
})
