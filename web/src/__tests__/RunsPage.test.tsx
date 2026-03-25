import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { RunsPage } from '../pages/RunsPage'

function ok(body: unknown) {
  return { ok: true as const, status: 200, body }
}

function makeFetch(response: { ok: boolean; status: number; body: unknown }) {
  return vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: () => Promise.resolve(response.body),
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
    vi.stubGlobal('fetch', makeFetch(ok(EMPTY_RESPONSE)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument()
    })
    expect(screen.getByRole('status')).toHaveTextContent('No runs found')
  })
})

describe('RunsPage — populated state', () => {
  it('renders run table when runs exist', async () => {
    vi.stubGlobal('fetch', makeFetch(ok(ONE_RUN_RESPONSE)))
    renderPage()
    await waitFor(() => {
      // run_id is truncated to 8 chars; full ID is in title attribute
      expect(screen.getByTitle('run-abc-123')).toBeInTheDocument()
    })
  })

  it('shows succeeded status badge', async () => {
    vi.stubGlobal('fetch', makeFetch(ok(ONE_RUN_RESPONSE)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('succeeded')).toBeInTheDocument()
    })
  })

  it('shows playbook_id in table', async () => {
    vi.stubGlobal('fetch', makeFetch(ok(ONE_RUN_RESPONSE)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('meeting-notes-to-eos-rocks')).toBeInTheDocument()
    })
  })

  it('shows artifact count', async () => {
    vi.stubGlobal('fetch', makeFetch(ok(ONE_RUN_RESPONSE)))
    renderPage()
    await waitFor(() => {
      // artifact_count is 3
      expect(screen.getByText('3')).toBeInTheDocument()
    })
  })
})

describe('RunsPage — error state', () => {
  it('shows error state on fetch failure', async () => {
    vi.stubGlobal('fetch', makeFetch({ ok: false, status: 503, body: { detail: 'Service unavailable' } }))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('shows Retry button on error', async () => {
    vi.stubGlobal('fetch', makeFetch({ ok: false, status: 503, body: { detail: 'Service unavailable' } }))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    })
  })
})

describe('RunsPage — refresh', () => {
  it('renders Refresh button', async () => {
    vi.stubGlobal('fetch', makeFetch(ok(EMPTY_RESPONSE)))
    renderPage()
    await waitFor(() => screen.getByRole('button', { name: 'Refresh' }))
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument()
  })

  it('calls fetch again when Refresh is clicked', async () => {
    const mockFetch = makeFetch(ok(EMPTY_RESPONSE))
    vi.stubGlobal('fetch', mockFetch)
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => screen.getByRole('button', { name: 'Refresh' }))
    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })
  })
})
