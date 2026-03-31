import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { RetryButton } from '../components/RetryButton'
import type { RunDetail } from '../types'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function makeRun(overrides: Partial<RunDetail> = {}): RunDetail {
  return {
    run_id: 'run-001',
    status: 'failed',
    source: 'api_sync',
    job_id: null,
    request_id: null,
    mode: 'deterministic',
    template_id: null,
    playbook_id: null,
    profile: 'dev',
    started_at: '2026-03-24T10:00:00Z',
    completed_at: '2026-03-24T10:00:02Z',
    total_ms: 2000,
    error_category: 'system',
    error_message: 'Something went wrong',
    manifest_path: null,
    replay_available: true,
    ...overrides,
  }
}

function renderBtn(run: RunDetail) {
  return render(
    <MemoryRouter>
      <RetryButton run={run} />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
  mockNavigate.mockReset()
})

describe('RetryButton', () => {
  it('renders for failed run with replay_available', () => {
    renderBtn(makeRun())
    expect(screen.getByRole('button', { name: 'Retry this run' })).toBeInTheDocument()
  })

  it('does not render for non-failed run', () => {
    renderBtn(makeRun({ status: 'succeeded' }))
    expect(screen.queryByRole('button', { name: 'Retry this run' })).not.toBeInTheDocument()
  })

  it('does not render when replay_available is false', () => {
    renderBtn(makeRun({ replay_available: false }))
    expect(screen.queryByRole('button', { name: 'Retry this run' })).not.toBeInTheDocument()
  })

  it('does not render when replay_available is undefined', () => {
    renderBtn(makeRun({ replay_available: undefined }))
    expect(screen.queryByRole('button', { name: 'Retry this run' })).not.toBeInTheDocument()
  })

  it('shows loading state while retrying', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(
      () => new Promise(() => {}) // never resolves
    ))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: 'Retry this run' }))
    expect(screen.getByText('Retrying…')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('navigates to new run on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        run_id: 'run-new',
        source_run_id: 'run-001',
        action_type: 'retry',
        job_id: 'job-001',
      }),
    }))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: 'Retry this run' }))
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/runs/run-new')
    })
  })

  it('shows error on failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: 'No input text' }),
    }))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: 'Retry this run' }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('re-enables button after error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: 'No input text' }),
    }))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: 'Retry this run' }))
    await waitFor(() => screen.getByRole('alert'))
    expect(screen.getByRole('button')).not.toBeDisabled()
  })
})
