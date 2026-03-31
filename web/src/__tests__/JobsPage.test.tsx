import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { JobsPage } from '../pages/JobsPage'

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
      <JobsPage />
    </MemoryRouter>
  )
}

const EMPTY_RESPONSE = { jobs: [], total: 0, limit: 50, offset: 0 }

const ONE_JOB_RESPONSE = {
  jobs: [
    {
      job_id: 'job-abc-12345678',
      run_id: 'run-xyz-12345678',
      status: 'queued',
      workload_type: 'interactive',
      submitted_at: '2026-03-24T10:00:00.000Z',
      started_at: null,
      completed_at: null,
      retry_count: 0,
      error_category: null,
      error_message: null,
      output_path: null,
      playbook_id: null,
      action_type: null,
      source_run_id: null,
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('JobsPage', () => {
  it('shows empty state when no jobs', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(EMPTY_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument()
    })
    expect(screen.getByRole('status')).toHaveTextContent('No jobs found')
  })

  it('renders jobs table when jobs exist', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(ONE_JOB_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByTitle('job-abc-12345678')).toBeInTheDocument()
    })
  })

  it('shows job status badge', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(ONE_JOB_RESPONSE)]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('queued')).toBeInTheDocument()
    })
  })

  it('renders Refresh button', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(EMPTY_RESPONSE)]))
    renderPage()
    await waitFor(() => screen.getByRole('button', { name: 'Refresh' }))
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument()
  })

  it('renders filter buttons', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([ok(EMPTY_RESPONSE)]))
    renderPage()
    await waitFor(() => screen.getByRole('button', { name: 'All' }))
    expect(screen.getByRole('button', { name: 'Queued' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Running' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Failed' })).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([err(503, { detail: 'Unavailable' })]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('calls fetch again when Refresh is clicked', async () => {
    const mockFetch = makeFetchQueue([ok(EMPTY_RESPONSE), ok(EMPTY_RESPONSE)])
    vi.stubGlobal('fetch', mockFetch)
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => screen.getByRole('button', { name: 'Refresh' }))
    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })
  })

  it('calls fetch with status filter when filter button clicked', async () => {
    const mockFetch = makeFetchQueue([ok(EMPTY_RESPONSE), ok(EMPTY_RESPONSE)])
    vi.stubGlobal('fetch', mockFetch)
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => screen.getByRole('button', { name: 'Failed' }))
    await user.click(screen.getByRole('button', { name: 'Failed' }))
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })
    const secondCall = mockFetch.mock.calls[1][0] as string
    expect(secondCall).toContain('status=failed')
  })
})
