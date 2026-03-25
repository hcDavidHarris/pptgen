import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RunStatusBadge } from '../components/RunStatusBadge'
import type { RunStatus } from '../types'

const STATUSES: RunStatus[] = ['succeeded', 'running', 'failed', 'cancelled']

describe('RunStatusBadge', () => {
  it.each(STATUSES)('renders %s with correct class', (status) => {
    render(<RunStatusBadge status={status} />)
    const badge = screen.getByText(status)
    expect(badge).toHaveClass('run-status-badge')
    expect(badge).toHaveClass(`run-status-badge--${status}`)
  })

  it('renders the status text', () => {
    render(<RunStatusBadge status="succeeded" />)
    expect(screen.getByText('succeeded')).toBeInTheDocument()
  })
})
