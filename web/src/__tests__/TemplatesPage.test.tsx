import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { TemplatesPage } from '../pages/TemplatesPage'

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

function ok(body: unknown) {
  return { ok: true as const, status: 200, body }
}

function err(status: number, body: unknown) {
  return { ok: false as const, status, body }
}

function makeFetchQueue(responses: Array<{ ok: boolean; status: number; body: unknown }>) {
  let i = 0
  return vi.fn().mockImplementation(() => {
    const r = responses[Math.min(i++, responses.length - 1)]
    return Promise.resolve({
      ok: r.ok,
      status: r.status,
      json: () => Promise.resolve(r.body),
    })
  })
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

// Legacy /v1/templates response
const IDS_RESPONSE = { request_id: 'req-001', templates: ['exec_brief', 'arch_overview'] }

const EXEC_BRIEF_DETAIL = {
  template_id: 'exec_brief',
  name: 'Executive Brief',
  description: 'Exec deck',
  owner: 'Analytics',
  lifecycle_status: 'approved',
  versions: ['1.0.0'],
}

const ARCH_OVERVIEW_DETAIL = {
  template_id: 'arch_overview',
  name: 'Architecture Overview',
  description: null,
  owner: null,
  lifecycle_status: 'draft',
  versions: ['1.0.0', '2.0.0'],
}

function renderPage() {
  return render(
    <MemoryRouter>
      <TemplatesPage />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TemplatesPage', () => {
  it('shows empty state when no templates', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok({ request_id: 'r', templates: [] }),  // /v1/templates (IDs)
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument()
    })
    expect(screen.getByRole('status')).toHaveTextContent('No templates registered')
  })

  it('renders template table with loaded templates', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(IDS_RESPONSE),              // /v1/templates → IDs
      ok(EXEC_BRIEF_DETAIL),         // /v1/templates/exec_brief
      ok(ARCH_OVERVIEW_DETAIL),      // /v1/templates/arch_overview
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Executive Brief')).toBeInTheDocument()
    })
    expect(screen.getByText('Architecture Overview')).toBeInTheDocument()
  })

  it('shows template IDs as code elements', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok({ request_id: 'r', templates: ['exec_brief'] }),
      ok(EXEC_BRIEF_DETAIL),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('exec_brief')).toBeInTheDocument()
    })
  })

  it('shows lifecycle status', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok({ request_id: 'r', templates: ['exec_brief'] }),
      ok(EXEC_BRIEF_DETAIL),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('approved')).toBeInTheDocument()
    })
  })

  it('shows latest version', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok({ request_id: 'r', templates: ['arch_overview'] }),
      ok(ARCH_OVERVIEW_DETAIL),
    ]))
    renderPage()
    await waitFor(() => {
      // Latest is the last in the list: 2.0.0
      expect(screen.getByText('2.0.0')).toBeInTheDocument()
    })
  })

  it('shows error state on fetch failure', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      err(503, { detail: 'Service unavailable' }),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('shows owner when available', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok({ request_id: 'r', templates: ['exec_brief'] }),
      ok(EXEC_BRIEF_DETAIL),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Analytics')).toBeInTheDocument()
    })
  })

  it('navigates to template detail on row click', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok({ request_id: 'r', templates: ['exec_brief'] }),
      ok(EXEC_BRIEF_DETAIL),
    ]))
    const { container } = renderPage()
    await waitFor(() => {
      expect(screen.getByText('Executive Brief')).toBeInTheDocument()
    })
    const row = container.querySelector('.template-table__row')
    expect(row).toBeInTheDocument()
  })
})
