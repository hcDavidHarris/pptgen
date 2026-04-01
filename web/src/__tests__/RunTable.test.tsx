import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { RunTable } from '../components/RunTable'
import type { RunListItem } from '../types'

function makeRun(overrides: Partial<RunListItem> = {}): RunListItem {
  return {
    run_id: 'run-abcdef12-0000-0000-0000-000000000000',
    status: 'succeeded',
    source: 'api_sync',
    job_id: null,
    mode: 'deterministic',
    template_id: 'hc-default',
    playbook_id: 'meeting-notes',
    started_at: '2026-03-24T10:00:00.000Z',
    completed_at: '2026-03-24T10:00:02.500Z',
    total_ms: 2500,
    error_category: null,
    artifact_count: 3,
    ...overrides,
  }
}

function renderTable(runs: RunListItem[]) {
  return render(
    <MemoryRouter>
      <RunTable runs={runs} />
    </MemoryRouter>
  )
}

describe('RunTable — basic rendering', () => {
  it('renders column headers', () => {
    renderTable([])
    expect(screen.getByRole('columnheader', { name: 'Run ID' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Status' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Playbook' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Duration' })).toBeInTheDocument()
  })

  it('renders a row for each run', () => {
    renderTable([makeRun(), makeRun({ run_id: 'run-bbbbbbbb-0000-0000-0000-000000000000' })])
    // tbody rows have role="link", so we count those
    expect(screen.getAllByRole('link')).toHaveLength(2)
  })
})

describe('RunTable — run_id truncation', () => {
  it('truncates run_id to 8 chars with ellipsis', () => {
    renderTable([makeRun({ run_id: 'run-abcdef12-1234-5678-abcd-ef1234567890' })])
    expect(screen.getByText('run-abcd…')).toBeInTheDocument()
  })

  it('shows full run_id in title attribute', () => {
    const fullId = 'run-abcdef12-1234-5678-abcd-ef1234567890'
    renderTable([makeRun({ run_id: fullId })])
    const cell = screen.getByTitle(fullId)
    expect(cell).toBeInTheDocument()
  })
})

describe('RunTable — failed row highlight', () => {
  it('adds failed class to failed rows', () => {
    renderTable([makeRun({ status: 'failed' })])
    const row = screen.getByRole('link', { name: /Run run-abcdef/ })
    expect(row).toHaveClass('run-table__row--failed')
  })

  it('does not add failed class to succeeded rows', () => {
    renderTable([makeRun({ status: 'succeeded' })])
    const row = screen.getByRole('link', { name: /Run run-abcdef/ })
    expect(row).not.toHaveClass('run-table__row--failed')
  })
})

describe('RunTable — duration display', () => {
  it('shows formatted duration when total_ms present', () => {
    renderTable([makeRun({ total_ms: 2500 })])
    expect(screen.getByText('2.5 s')).toBeInTheDocument()
  })

  it('shows em dash when total_ms null, not running, and no completed_at', () => {
    renderTable([makeRun({ total_ms: null, status: 'failed', completed_at: null })])
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})

describe('RunTable — playbook column', () => {
  it('shows playbook_id when present', () => {
    renderTable([makeRun({ playbook_id: 'my-playbook' })])
    expect(screen.getByText('my-playbook')).toBeInTheDocument()
  })

  it('shows em dash when playbook_id is null', () => {
    renderTable([makeRun({ playbook_id: null })])
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
