import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RunStatsCard } from '../components/RunStatsCard'
import type { RunStats } from '../types'

function makeStats(overrides: Partial<RunStats> = {}): RunStats {
  return {
    window_hours: 24,
    total_runs: 10,
    succeeded_runs: 8,
    failed_runs: 2,
    running_runs: 0,
    success_rate: 80.0,
    avg_duration_ms: 1500,
    ...overrides,
  }
}

describe('RunStatsCard', () => {
  it('shows loading state', () => {
    const { container } = render(<RunStatsCard stats={null} loading={true} error={null} />)
    expect(screen.getByText('Loading stats…')).toBeTruthy()
    // aria-busy is set
    expect(container.querySelector('[aria-busy="true"]')).toBeTruthy()
  })

  it('shows unavailable when error', () => {
    render(<RunStatsCard stats={null} loading={false} error={new Error('fail')} />)
    expect(screen.getByText('Stats unavailable')).toBeTruthy()
  })

  it('shows unavailable when no stats and no loading', () => {
    render(<RunStatsCard stats={null} loading={false} error={null} />)
    expect(screen.getByText('Stats unavailable')).toBeTruthy()
  })

  it('renders total runs', () => {
    render(<RunStatsCard stats={makeStats({ total_runs: 42 })} loading={false} error={null} />)
    expect(screen.getByText('42')).toBeTruthy()
    expect(screen.getByText('Total')).toBeTruthy()
  })

  it('renders success rate as percentage', () => {
    render(<RunStatsCard stats={makeStats({ success_rate: 75.0 })} loading={false} error={null} />)
    expect(screen.getByText('75%')).toBeTruthy()
  })

  it('renders null success rate as em-dash', () => {
    render(<RunStatsCard stats={makeStats({ success_rate: null, total_runs: 0 })} loading={false} error={null} />)
    // Two em-dashes: success_rate and avg_duration_ms
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })

  it('renders failed count', () => {
    render(<RunStatsCard stats={makeStats({ failed_runs: 3 })} loading={false} error={null} />)
    expect(screen.getByText('3')).toBeTruthy()
  })

  it('applies warn class when failed_runs > 0', () => {
    const { container } = render(
      <RunStatsCard stats={makeStats({ failed_runs: 2 })} loading={false} error={null} />
    )
    expect(container.querySelector('.run-stats-card__stat--warn')).toBeTruthy()
  })

  it('does not apply warn class when failed_runs === 0', () => {
    const { container } = render(
      <RunStatsCard stats={makeStats({ failed_runs: 0 })} loading={false} error={null} />
    )
    expect(container.querySelector('.run-stats-card__stat--warn')).toBeFalsy()
  })

  it('renders avg duration in ms for small values', () => {
    render(<RunStatsCard stats={makeStats({ avg_duration_ms: 250 })} loading={false} error={null} />)
    expect(screen.getByText('250 ms')).toBeTruthy()
  })

  it('renders avg duration in seconds for >= 1000ms', () => {
    render(<RunStatsCard stats={makeStats({ avg_duration_ms: 2500 })} loading={false} error={null} />)
    expect(screen.getByText('2.5 s')).toBeTruthy()
  })

  it('renders avg duration in minutes for >= 60s', () => {
    render(<RunStatsCard stats={makeStats({ avg_duration_ms: 90_000 })} loading={false} error={null} />)
    expect(screen.getByText('1.5 min')).toBeTruthy()
  })

  it('renders null avg duration as em-dash', () => {
    render(<RunStatsCard stats={makeStats({ avg_duration_ms: null })} loading={false} error={null} />)
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })

  it('does not show running stat when running_runs === 0', () => {
    render(<RunStatsCard stats={makeStats({ running_runs: 0 })} loading={false} error={null} />)
    expect(screen.queryByText('Running')).toBeFalsy()
  })

  it('shows running stat with running class when running_runs > 0', () => {
    const { container } = render(
      <RunStatsCard stats={makeStats({ running_runs: 3 })} loading={false} error={null} />
    )
    expect(screen.getByText('Running')).toBeTruthy()
    expect(container.querySelector('.run-stats-card__stat--running')).toBeTruthy()
  })

  it('shows window label for 24h', () => {
    render(<RunStatsCard stats={makeStats()} loading={false} error={null} window="24h" />)
    expect(screen.getByText('Last 24 hours')).toBeTruthy()
  })

  it('shows window label for 7d', () => {
    render(<RunStatsCard stats={makeStats()} loading={false} error={null} window="7d" />)
    expect(screen.getByText('Last 7 days')).toBeTruthy()
  })

  it('shows window label for 1h', () => {
    render(<RunStatsCard stats={makeStats()} loading={false} error={null} window="1h" />)
    expect(screen.getByText('Last 1 hour')).toBeTruthy()
  })

  it('falls back to raw window string for unknown values', () => {
    render(<RunStatsCard stats={makeStats()} loading={false} error={null} window="48h" />)
    expect(screen.getByText('Last 48h')).toBeTruthy()
  })

  it('has aria-label on the card', () => {
    const { container } = render(<RunStatsCard stats={makeStats()} loading={false} error={null} />)
    expect(container.querySelector('[aria-label="Run summary stats"]')).toBeTruthy()
  })
})
