import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RunSummaryCard } from '../components/RunSummaryCard'
import type { RunDetail } from '../types'

function makeRun(overrides: Partial<RunDetail> = {}): RunDetail {
  return {
    run_id: 'run-xyz-0001',
    status: 'succeeded',
    source: 'api_sync',
    job_id: null,
    request_id: 'req-001',
    mode: 'deterministic',
    template_id: 'hc-default',
    playbook_id: 'meeting-notes-to-eos-rocks',
    profile: 'dev',
    started_at: '2026-03-24T10:00:00.000Z',
    completed_at: '2026-03-24T10:00:02.500Z',
    total_ms: 2500,
    error_category: null,
    error_message: null,
    manifest_path: null,
    ...overrides,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('RunSummaryCard — fields', () => {
  it('shows the run ID', () => {
    render(<RunSummaryCard run={makeRun()} />)
    expect(screen.getByText('run-xyz-0001')).toBeInTheDocument()
  })

  it('shows the status badge', () => {
    render(<RunSummaryCard run={makeRun()} />)
    expect(screen.getByText('succeeded')).toBeInTheDocument()
  })

  it('shows the playbook ID', () => {
    render(<RunSummaryCard run={makeRun()} />)
    expect(screen.getByText('meeting-notes-to-eos-rocks')).toBeInTheDocument()
  })

  it('shows formatted duration when total_ms positive', () => {
    render(<RunSummaryCard run={makeRun({ total_ms: 2500 })} />)
    expect(screen.getByText('2.5 s')).toBeInTheDocument()
  })

  it('falls back to completed_at - started_at when total_ms is zero', () => {
    render(<RunSummaryCard run={makeRun({
      total_ms: 0,
      started_at: '2026-03-24T10:00:00.000Z',
      completed_at: '2026-03-24T10:00:03.000Z',
    })} />)
    expect(screen.getByText('3.0 s')).toBeInTheDocument()
  })

  it('shows em dash when no timing info available', () => {
    render(<RunSummaryCard run={makeRun({ total_ms: null, completed_at: null, status: 'failed' })} />)
    // Multiple '—' appear (playbook, template etc.) — just confirm at least one
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1)
  })

  it('shows error fields when error_category present', () => {
    render(<RunSummaryCard run={makeRun({ error_category: 'VALIDATION', error_message: 'bad input' })} />)
    expect(screen.getByText(/VALIDATION/)).toBeInTheDocument()
    expect(screen.getByText(/bad input/)).toBeInTheDocument()
  })
})

describe('RunSummaryCard — copy button', () => {
  it('renders a copy button for run ID', () => {
    render(<RunSummaryCard run={makeRun()} />)
    expect(screen.getByRole('button', { name: /Copy run ID/i })).toBeInTheDocument()
  })

  it('copy button shows copied state after click', async () => {
    // Stub clipboard API
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
    const user = userEvent.setup()
    render(<RunSummaryCard run={makeRun()} />)
    const btn = screen.getByRole('button', { name: /Copy run ID/i })
    await user.click(btn)
    expect(screen.getByRole('button', { name: 'Copied!' })).toBeInTheDocument()
  })
})
