import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TemplateDetailPage } from '../pages/TemplateDetailPage'

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

const DETAIL_RESPONSE = {
  template_id: 'exec_brief',
  name: 'Executive Brief',
  description: 'Concise deck for leadership.',
  owner: 'Analytics Services',
  lifecycle_status: 'approved',
  versions: ['1.0.0', '2.0.0'],
}

const VERSIONS_RESPONSE = [
  {
    version: '1.0.0',
    template_revision_hash: 'ab12cd34ef56ab12',
    template_path: 'templates/exec_brief/v1/template.pptx',
    playbook_path: null,
    input_contract_version: 'executive_v1',
    ai_mode: 'optional',
  },
  {
    version: '2.0.0',
    template_revision_hash: 'cd34ef56ab12cd34',
    template_path: 'templates/exec_brief/v2/template.pptx',
    playbook_path: null,
    input_contract_version: 'executive_v2',
    ai_mode: 'optional',
  },
]

const RUNS_RESPONSE = {
  template_id: 'exec_brief',
  runs: [
    {
      run_id: 'run-aabbccdd001122334455',
      status: 'succeeded',
      template_version: '1.0.0',
      template_revision_hash: 'ab12cd34ef56ab12',
      started_at: '2026-03-24T10:00:00.000Z',
      completed_at: '2026-03-24T10:00:05.000Z',
      total_ms: 5000,
      artifact_count: 2,
      error_category: null,
      mode: 'deterministic',
      playbook_id: 'executive_brief',
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
}

const EMPTY_RUNS_RESPONSE = {
  template_id: 'exec_brief',
  runs: [],
  total: 0,
  limit: 50,
  offset: 0,
}

function renderPage(templateId = 'exec_brief') {
  return render(
    <MemoryRouter initialEntries={[`/templates/${templateId}`]}>
      <Routes>
        <Route path="/templates/:templateId" element={<TemplateDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TemplateDetailPage', () => {
  it('shows loading state initially', () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('renders template name after loading', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Executive Brief')).toBeInTheDocument()
    })
  })

  it('shows template ID', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('exec_brief')).toBeInTheDocument()
    })
  })

  it('shows owner and description', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Analytics Services')).toBeInTheDocument()
      expect(screen.getByText('Concise deck for leadership.')).toBeInTheDocument()
    })
  })

  it('shows lifecycle status badge', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      const badges = screen.getAllByText('approved')
      expect(badges.length).toBeGreaterThan(0)
    })
  })

  it('shows version history table', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      // Both versions appear (possibly multiple times across metadata + tables)
      expect(screen.getAllByText('1.0.0').length).toBeGreaterThan(0)
      expect(screen.getAllByText('2.0.0').length).toBeGreaterThan(0)
    })
  })

  it('shows revision hashes in version table', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('ab12cd34ef56ab12')).toBeInTheDocument()
    })
  })

  it('shows usage card with runs count', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Usage (last 30 days)')).toBeInTheDocument()
    })
  })

  it('shows empty usage when no runs', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(EMPTY_RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No runs in the last 30 days.')).toBeInTheDocument()
    })
  })

  it('shows back link to templates', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('← Back to Templates')).toBeInTheDocument()
    })
  })

  it('shows error state on fetch failure', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      err(404, { detail: 'Template not found: exec_brief' }),
      err(404, { detail: 'Template not found: exec_brief' }),
      ok(EMPTY_RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('shows Version History section heading', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ok(DETAIL_RESPONSE),
      ok(VERSIONS_RESPONSE),
      ok(RUNS_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeInTheDocument()
    })
  })
})
