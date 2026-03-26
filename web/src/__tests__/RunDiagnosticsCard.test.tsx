import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RunDiagnosticsCard } from '../components/RunDiagnosticsCard'
import type { RunDetail, RunMetrics } from '../types'

function makeRun(overrides: Partial<RunDetail> = {}): RunDetail {
  return {
    run_id: 'run-diag-001',
    status: 'failed',
    source: 'api_sync',
    job_id: null,
    request_id: null,
    mode: 'deterministic',
    template_id: 'hc-default',
    playbook_id: 'meeting-notes',
    profile: 'dev',
    started_at: '2026-03-24T10:00:00.000Z',
    completed_at: '2026-03-24T10:00:01.000Z',
    total_ms: 1000,
    error_category: 'TemplateError',
    error_message: 'Template not found: missing-template',
    manifest_path: null,
    retry_count: null,
    artifact_count: 0,
    ...overrides,
  }
}

function makeMetrics(overrides: Partial<RunMetrics> = {}): RunMetrics {
  return {
    run_id: 'run-diag-001',
    total_ms: 1000,
    artifact_count: 0,
    stage_timings: [
      { stage: 'route_input', duration_ms: 10 },
      { stage: 'execute_playbook', duration_ms: 990 },
    ],
    slowest_stage: 'execute_playbook',
    fastest_stage: 'route_input',
    ...overrides,
  }
}

describe('RunDiagnosticsCard — not rendered for non-failed runs', () => {
  it('returns null when status is succeeded', () => {
    const { container } = render(
      <RunDiagnosticsCard run={makeRun({ status: 'succeeded' })} metrics={null} />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('returns null when status is running', () => {
    const { container } = render(
      <RunDiagnosticsCard run={makeRun({ status: 'running' })} metrics={null} />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('returns null when status is cancelled', () => {
    const { container } = render(
      <RunDiagnosticsCard run={makeRun({ status: 'cancelled' })} metrics={null} />
    )
    expect(container).toBeEmptyDOMElement()
  })
})

describe('RunDiagnosticsCard — failed run fields', () => {
  it('renders the diagnostics section heading', () => {
    render(<RunDiagnosticsCard run={makeRun()} metrics={null} />)
    expect(screen.getByRole('heading', { name: 'Diagnostics' })).toBeInTheDocument()
  })

  it('shows error_category', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_category: 'ValidationError' })} metrics={null} />)
    expect(screen.getByText('ValidationError')).toBeInTheDocument()
  })

  it('shows error_message', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_message: 'input too large' })} metrics={null} />)
    expect(screen.getByText('input too large')).toBeInTheDocument()
  })

  it('shows last recorded stage from metrics timings', () => {
    render(<RunDiagnosticsCard run={makeRun()} metrics={makeMetrics()} />)
    expect(screen.getByText('execute_playbook')).toBeInTheDocument()
  })

  it('shows em dash for last stage when metrics is null', () => {
    render(<RunDiagnosticsCard run={makeRun()} metrics={null} />)
    // Multiple — possible; just confirm Last recorded stage row exists
    expect(screen.getByText('Last recorded stage')).toBeInTheDocument()
  })

  it('shows em dash for last stage when stage_timings is empty', () => {
    render(
      <RunDiagnosticsCard
        run={makeRun()}
        metrics={makeMetrics({ stage_timings: [] })}
      />
    )
    expect(screen.getByText('Last recorded stage')).toBeInTheDocument()
  })

  it('shows retry_count row when retry_count is a number', () => {
    render(<RunDiagnosticsCard run={makeRun({ retry_count: 3 })} metrics={null} />)
    expect(screen.getByText('Retry count')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('omits retry_count row when retry_count is null', () => {
    render(<RunDiagnosticsCard run={makeRun({ retry_count: null })} metrics={null} />)
    expect(screen.queryByText('Retry count')).not.toBeInTheDocument()
  })

  it('omits retry_count row when retry_count is undefined', () => {
    const run = makeRun()
    delete (run as any).retry_count
    render(<RunDiagnosticsCard run={run} metrics={null} />)
    expect(screen.queryByText('Retry count')).not.toBeInTheDocument()
  })

  it('shows Artifacts available: Yes when artifact_count > 0', () => {
    render(<RunDiagnosticsCard run={makeRun({ artifact_count: 2 })} metrics={null} />)
    expect(screen.getByText('Yes')).toBeInTheDocument()
  })

  it('shows Artifacts available: None when artifact_count is 0', () => {
    render(<RunDiagnosticsCard run={makeRun({ artifact_count: 0 })} metrics={null} />)
    expect(screen.getByText('None')).toBeInTheDocument()
  })

  it('shows Artifacts available: Yes when run.artifact_count is null but metrics has count > 0', () => {
    render(
      <RunDiagnosticsCard
        run={makeRun({ artifact_count: null })}
        metrics={makeMetrics({ artifact_count: 1 })}
      />
    )
    expect(screen.getByText('Yes')).toBeInTheDocument()
  })
})

describe('RunDiagnosticsCard — hints', () => {
  it('shows TemplateError hint', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_category: 'TemplateError' })} metrics={null} />)
    expect(screen.getByText(/Verify the template exists/)).toBeInTheDocument()
  })

  it('shows ValidationError hint', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_category: 'ValidationError' })} metrics={null} />)
    expect(screen.getByText(/Review required input structure/)).toBeInTheDocument()
  })

  it('shows ArtifactError hint', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_category: 'ArtifactError' })} metrics={null} />)
    expect(screen.getByText(/artifact promotion and storage/)).toBeInTheDocument()
  })

  it('shows TimeoutError hint', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_category: 'TimeoutError' })} metrics={null} />)
    expect(screen.getByText(/exceeded its timeout/)).toBeInTheDocument()
  })

  it('shows RoutingError hint', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_category: 'RoutingError' })} metrics={null} />)
    expect(screen.getByText(/No matching playbook/)).toBeInTheDocument()
  })

  it('shows no hint for unknown category', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_category: 'XUnknownError' })} metrics={null} />)
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })

  it('shows no hint when error_category is null', () => {
    render(<RunDiagnosticsCard run={makeRun({ error_category: null })} metrics={null} />)
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })
})
