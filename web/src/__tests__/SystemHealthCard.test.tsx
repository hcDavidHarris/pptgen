import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SystemHealthCard } from '../components/SystemHealthCard'
import type { SystemHealth } from '../types'

function makeHealth(overrides: Partial<SystemHealth> = {}): SystemHealth {
  return {
    status: 'healthy',
    queued_jobs: 0,
    running_jobs: 0,
    failed_jobs_1h: 0,
    run_store_ok: true,
    job_store_ok: true,
    ...overrides,
  }
}

describe('SystemHealthCard', () => {
  it('shows loading state', () => {
    const { container } = render(<SystemHealthCard health={null} loading={true} error={null} />)
    expect(screen.getByText('Loading…')).toBeTruthy()
    expect(container.querySelector('[aria-busy="true"]')).toBeTruthy()
  })

  it('shows unavailable on error', () => {
    render(<SystemHealthCard health={null} loading={false} error={new Error('fail')} />)
    expect(screen.getByText('Health unavailable')).toBeTruthy()
  })

  it('shows unavailable when no health and not loading', () => {
    render(<SystemHealthCard health={null} loading={false} error={null} />)
    expect(screen.getByText('Health unavailable')).toBeTruthy()
  })

  it('shows Healthy badge when status is healthy', () => {
    render(<SystemHealthCard health={makeHealth()} loading={false} error={null} />)
    expect(screen.getByText('Healthy')).toBeTruthy()
  })

  it('shows Degraded badge when status is degraded', () => {
    render(<SystemHealthCard health={makeHealth({ status: 'degraded' })} loading={false} error={null} />)
    expect(screen.getByText('Degraded')).toBeTruthy()
  })

  it('applies healthy CSS class', () => {
    const { container } = render(<SystemHealthCard health={makeHealth()} loading={false} error={null} />)
    expect(container.querySelector('.system-health-card--healthy')).toBeTruthy()
  })

  it('applies degraded CSS class', () => {
    const { container } = render(
      <SystemHealthCard health={makeHealth({ status: 'degraded' })} loading={false} error={null} />
    )
    expect(container.querySelector('.system-health-card--degraded')).toBeTruthy()
  })

  it('shows queue depth', () => {
    render(<SystemHealthCard health={makeHealth({ queued_jobs: 5 })} loading={false} error={null} />)
    expect(screen.getByText('5')).toBeTruthy()
    expect(screen.getByText('Queued')).toBeTruthy()
  })

  it('shows running count', () => {
    render(<SystemHealthCard health={makeHealth({ running_jobs: 3 })} loading={false} error={null} />)
    expect(screen.getByText('3')).toBeTruthy()
    expect(screen.getByText('Running')).toBeTruthy()
  })

  it('shows failed 1h with warn class when > 0', () => {
    const { container } = render(
      <SystemHealthCard health={makeHealth({ failed_jobs_1h: 2 })} loading={false} error={null} />
    )
    expect(screen.getByText('2')).toBeTruthy()
    expect(container.querySelector('.system-health-card__stat--warn')).toBeTruthy()
  })

  it('does not show warn class when failed_jobs_1h is 0', () => {
    const { container } = render(
      <SystemHealthCard health={makeHealth({ failed_jobs_1h: 0 })} loading={false} error={null} />
    )
    expect(container.querySelector('.system-health-card__stat--warn')).toBeFalsy()
  })

  it('shows store unavailable message when run_store_ok is false', () => {
    render(
      <SystemHealthCard
        health={makeHealth({ run_store_ok: false, status: 'degraded' })}
        loading={false}
        error={null}
      />
    )
    expect(screen.getByText(/run.*unavailable/i)).toBeTruthy()
  })

  it('shows store unavailable message when job_store_ok is false', () => {
    render(
      <SystemHealthCard
        health={makeHealth({ job_store_ok: false, status: 'degraded' })}
        loading={false}
        error={null}
      />
    )
    expect(screen.getByText(/job.*unavailable/i)).toBeTruthy()
  })

  it('does not show stores warning when all stores ok', () => {
    render(<SystemHealthCard health={makeHealth()} loading={false} error={null} />)
    expect(screen.queryByText(/unavailable/i)).toBeFalsy()
  })

  it('has aria-label on the card', () => {
    const { container } = render(<SystemHealthCard health={makeHealth()} loading={false} error={null} />)
    expect(container.querySelector('[aria-label="System health"]')).toBeTruthy()
  })
})
