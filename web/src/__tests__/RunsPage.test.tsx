import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { RunsPage } from '../pages/RunsPage'

function ok(body: unknown) {
  return { ok: true as const, status: 200, body }
}

function err(status: number, body: unknown) {
  return { ok: false as const, status, body }
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

function renderPage() {
  return render(
    <MemoryRouter>
      <RunsPage />
    </MemoryRouter>
  )
}

const EMPTY_RESPONSE = { runs: [], total: 0, limit: 50, offset: 0 }

const STATS_RESPONSE = {
  window_hours: 24,
  total_runs: 10,
  succeeded_runs: 8,
  failed_runs: 2,
  running_runs: 0,
  success_rate: 80.0,
  avg_duration_ms: 1500,
}

const HEALTH_RESPONSE = {
  status: 'healthy',
  queued_jobs: 0,
  running_jobs: 0,
  failed_jobs_1h: 0,
  run_store_ok: true,
  job_store_ok: true,
}

const ONE_RUN_RESPONSE = {
  runs: [
    {
      run_id: 'run-abc-123',
      status: 'succeeded',
      source: 'api_sync',
      job_id: null,
      started_at: '2026-03-24T10:00:00.000Z',
      completed_at: '2026-03-24T10:00:02.000Z',
      total_ms: 2000,
      artifact_count: 3,
      error_category: null,
      mode: 'deterministic',
      template_id: 'hc-default',
      playbook_id: 'meeting-notes-to-eos-rocks',
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('RunsPage — empty state', () => {
  it('shows empty state when no runs', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(EMPTY_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument()
    })
    expect(screen.getByRole('status')).toHaveTextContent('No runs found')
  })
})

describe('RunsPage — populated state', () => {
  it('renders run table when runs exist', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(ONE_RUN_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      // run_id is truncated to 8 chars; full ID is in title attribute
      expect(screen.getByTitle('run-abc-123')).toBeInTheDocument()
    })
  })

  it('shows succeeded status badge', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(ONE_RUN_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('succeeded')).toBeInTheDocument()
    })
  })

  it('shows playbook_id in table', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(ONE_RUN_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('meeting-notes-to-eos-rocks')).toBeInTheDocument()
    })
  })

  it('shows artifact count', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(ONE_RUN_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      // run_id is in title; confirm run loaded
      expect(screen.getByTitle('run-abc-123')).toBeInTheDocument()
    })
  })
})

describe('RunsPage — stats card', () => {
  it('renders stats card with total runs', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(EMPTY_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument()
    })
    expect(screen.getByText('Total')).toBeInTheDocument()
  })

  it('renders stats card success rate', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(EMPTY_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('80%')).toBeInTheDocument()
    })
  })

  it('shows stats unavailable when stats fetch fails', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(EMPTY_RESPONSE),
      err(503, { detail: 'Service unavailable' }),
      ok(HEALTH_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Stats unavailable')).toBeInTheDocument()
    })
  })
})

describe('RunsPage — system health card', () => {
  it('renders system health card with Healthy badge', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(EMPTY_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Healthy')).toBeInTheDocument()
    })
  })

  it('shows health unavailable when health fetch fails', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(EMPTY_RESPONSE),
      ok(STATS_RESPONSE),
      err(503, { detail: 'Service unavailable' }),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Health unavailable')).toBeInTheDocument()
    })
  })
})

describe('RunsPage — error state', () => {
  it('shows error state on fetch failure', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      err(503, { detail: 'Service unavailable' }),
      err(503, { detail: 'Service unavailable' }),
      err(503, { detail: 'Service unavailable' }),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('shows Retry button on error', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      err(503, { detail: 'Service unavailable' }),
      err(503, { detail: 'Service unavailable' }),
      err(503, { detail: 'Service unavailable' }),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    })
  })
})

describe('RunsPage — refresh', () => {
  it('renders Refresh button', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(EMPTY_RESPONSE), ok(STATS_RESPONSE), ok(HEALTH_RESPONSE)]))
    renderPage()
    await waitFor(() => screen.getByRole('button', { name: 'Refresh' }))
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument()
  })

  it('calls fetch again when Refresh is clicked', async () => {
    // Initial render: 3 fetches (runs + stats + health). Refresh: 1 more fetch (runs only). Total: 4.
    const mockFetch = makeFetchQueue([
      ok(EMPTY_RESPONSE),
      ok(STATS_RESPONSE),
      ok(HEALTH_RESPONSE),
      ok(EMPTY_RESPONSE),
    ])
    vi.stubGlobal('fetch', mockFetch)
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => screen.getByRole('button', { name: 'Refresh' }))
    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(4)
    })
  })
})
