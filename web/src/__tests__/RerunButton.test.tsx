import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { RerunButton } from '../components/RerunButton'
import type { RunDetail } from '../types'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function makeRun(overrides: Partial<RunDetail> = {}): RunDetail {
  return {
    run_id: 'run-001',
    status: 'succeeded',
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
    error_category: null,
    error_message: null,
    manifest_path: null,
    replay_available: true,
    ...overrides,
  }
}

function renderBtn(run: RunDetail) {
  return render(
    <MemoryRouter>
      <RerunButton run={run} />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
  mockNavigate.mockReset()
})

describe('RerunButton', () => {
  it('renders when replay_available is true', () => {
    renderBtn(makeRun())
    expect(screen.getByRole('button', { name: 'Rerun this run' })).toBeInTheDocument()
  })

  it('renders for failed runs too', () => {
    renderBtn(makeRun({ status: 'failed' }))
    expect(screen.getByRole('button', { name: 'Rerun this run' })).toBeInTheDocument()
  })

  it('does not render when replay_available is false', () => {
    renderBtn(makeRun({ replay_available: false }))
    expect(screen.queryByRole('button', { name: 'Rerun this run' })).not.toBeInTheDocument()
  })

  it('does not render when replay_available is undefined', () => {
    renderBtn(makeRun({ replay_available: undefined }))
    expect(screen.queryByRole('button', { name: 'Rerun this run' })).not.toBeInTheDocument()
  })

  it('shows loading state while rerunning', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Promise(() => {})))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: 'Rerun this run' }))
    expect(screen.getByText('Rerunning…')).toBeInTheDocument()
  })

  it('navigates to new run on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        run_id: 'run-new',
        source_run_id: 'run-001',
        action_type: 'rerun',
        job_id: null,
      }),
    }))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: 'Rerun this run' }))
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
    await user.click(screen.getByRole('button', { name: 'Rerun this run' }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
