import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBanner } from '../components/StatusBanner'
import { ApiError } from '../types'

describe('StatusBanner', () => {
  it('renders nothing when not loading and no error', () => {
    const { container } = render(<StatusBanner loading={false} error={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows loading message when loading', () => {
    render(<StatusBanner loading={true} loadingMessage="Planning deck…" error={null} />)
    expect(screen.getByRole('status')).toHaveTextContent('Planning deck…')
  })

  it('shows default loading message', () => {
    render(<StatusBanner loading={true} error={null} />)
    expect(screen.getByRole('status')).toHaveTextContent('Working…')
  })

  it('shows error message', () => {
    render(<StatusBanner loading={false} error={new Error('Something broke')} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Something broke')
  })

  it('shows request_id when error is ApiError with requestId', () => {
    const err = new ApiError('Bad mode', 400, 'req-err-001')
    render(<StatusBanner loading={false} error={err} />)
    expect(screen.getByRole('alert')).toHaveTextContent('req-err-001')
  })

  it('does not show request_id when ApiError has no requestId', () => {
    const err = new ApiError('Network error', 503, null)
    render(<StatusBanner loading={false} error={err} />)
    expect(screen.getByRole('alert')).not.toHaveTextContent('request_id')
  })

  it('loading takes precedence over error', () => {
    render(<StatusBanner loading={true} error={new Error('oops')} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
