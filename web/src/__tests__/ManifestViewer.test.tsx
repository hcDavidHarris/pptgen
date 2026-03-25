import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ManifestViewer } from '../components/ManifestViewer'

function ok(body: unknown) {
  return { ok: true as const, status: 200, body }
}

function makeFetch(response: { ok: boolean; status: number; body: unknown }) {
  return vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: () => Promise.resolve(response.body),
  })
}

const MANIFEST = { version: '1.0', run_id: 'run-xyz', artifacts: [] }

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('ManifestViewer — collapsed state', () => {
  it('shows Manifest toggle button', () => {
    render(<ManifestViewer runId="run-xyz" />)
    expect(screen.getByRole('button', { name: /Manifest/ })).toBeInTheDocument()
  })

  it('does not fetch manifest on mount', () => {
    const mockFetch = makeFetch(ok(MANIFEST))
    vi.stubGlobal('fetch', mockFetch)
    render(<ManifestViewer runId="run-xyz" />)
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('button has aria-expanded=false initially', () => {
    render(<ManifestViewer runId="run-xyz" />)
    expect(screen.getByRole('button', { name: /Manifest/ })).toHaveAttribute('aria-expanded', 'false')
  })
})

describe('ManifestViewer — expand on first click', () => {
  it('fetches manifest on first expand', async () => {
    const mockFetch = makeFetch(ok(MANIFEST))
    vi.stubGlobal('fetch', mockFetch)
    const user = userEvent.setup()
    render(<ManifestViewer runId="run-xyz" />)

    await user.click(screen.getByRole('button', { name: /Manifest/ }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })
  })

  it('renders manifest JSON after expand', async () => {
    vi.stubGlobal('fetch', makeFetch(ok(MANIFEST)))
    const user = userEvent.setup()
    render(<ManifestViewer runId="run-xyz" />)

    await user.click(screen.getByRole('button', { name: /Manifest/ }))

    await waitFor(() => {
      expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('true')
    })
    await waitFor(() => {
      expect(screen.getByText(/run-xyz/)).toBeInTheDocument()
    })
  })

  it('does not fetch again on collapse/re-expand', async () => {
    const mockFetch = makeFetch(ok(MANIFEST))
    vi.stubGlobal('fetch', mockFetch)
    const user = userEvent.setup()
    render(<ManifestViewer runId="run-xyz" />)

    // First expand → fetches
    await user.click(screen.getByRole('button', { name: /Manifest/ }))
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1))

    // Collapse
    await user.click(screen.getByRole('button', { name: /Manifest/ }))

    // Re-expand → no new fetch
    await user.click(screen.getByRole('button', { name: /Manifest/ }))
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })
})

describe('ManifestViewer — error state', () => {
  it('shows error message when manifest fetch fails', async () => {
    vi.stubGlobal('fetch', makeFetch({ ok: false, status: 404, body: { detail: 'not found' } }))
    const user = userEvent.setup()
    render(<ManifestViewer runId="run-xyz" />)

    await user.click(screen.getByRole('button', { name: /Manifest/ }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
