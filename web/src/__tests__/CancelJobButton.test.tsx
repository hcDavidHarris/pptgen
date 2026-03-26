import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { CancelJobButton } from '../components/CancelJobButton'
import type { RunDetail } from '../types'

function makeRun(overrides: Partial<RunDetail> = {}): RunDetail {
  return {
    run_id: 'run-001',
    status: 'running',
    source: 'api_async',
    job_id: 'job-abc',
    request_id: null,
    mode: 'deterministic',
    template_id: null,
    playbook_id: null,
    profile: 'dev',
    started_at: '2026-03-24T10:00:00Z',
    completed_at: null,
    total_ms: null,
    error_category: null,
    error_message: null,
    manifest_path: null,
    ...overrides,
  }
}

function renderBtn(run: RunDetail, onCancelled?: () => void) {
  return render(
    <MemoryRouter>
      <CancelJobButton run={run} onCancelled={onCancelled} />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('CancelJobButton', () => {
  it('renders for running run with job_id', () => {
    renderBtn(makeRun())
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('does not render for succeeded run', () => {
    renderBtn(makeRun({ status: 'succeeded' }))
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
  })

  it('does not render for failed run', () => {
    renderBtn(makeRun({ status: 'failed' }))
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
  })

  it('does not render when no job_id', () => {
    renderBtn(makeRun({ job_id: null }))
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
  })

  it('shows loading state while cancelling', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Promise(() => {})))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.getByText('Cancelling…')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('calls onCancelled callback on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        job_id: 'job-abc', accepted: true, status: 'cancellation_requested', message: 'ok',
      }),
    }))
    const onCancelled = vi.fn()
    const user = userEvent.setup()
    renderBtn(makeRun(), onCancelled)
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    await waitFor(() => {
      expect(onCancelled).toHaveBeenCalled()
    })
  })

  it('shows error on failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Not found' }),
    }))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('re-enables button after error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Not found' }),
    }))
    const user = userEvent.setup()
    renderBtn(makeRun())
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    await waitFor(() => screen.getByRole('alert'))
    expect(screen.getByRole('button')).not.toBeDisabled()
  })

  it('does not render for cancelled run', () => {
    renderBtn(makeRun({ status: 'cancelled' }))
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
  })
})
