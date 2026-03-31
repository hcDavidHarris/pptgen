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

// Governance responses (Phase 8 Stage 3)
// Fetch order: [0] detail, [1] versions (useTemplateDetail), [2] runs,
//              [3] versions-with-gov, [4] governance-state, [5] audit
const VERSIONS_WITH_GOV_RESPONSE = [
  {
    version: '1.0.0',
    template_revision_hash: 'ab12cd34ef56ab12',
    template_path: null,
    playbook_path: null,
    input_contract_version: 'executive_v1',
    ai_mode: 'optional',
    is_default: false,
    deprecated_at: null,
    deprecation_reason: null,
    promotion_timestamp: null,
  },
  {
    version: '2.0.0',
    template_revision_hash: 'cd34ef56ab12cd34',
    template_path: null,
    playbook_path: null,
    input_contract_version: 'executive_v2',
    ai_mode: 'optional',
    is_default: true,
    deprecated_at: null,
    deprecation_reason: null,
    promotion_timestamp: '2026-03-01T00:00:00Z',
  },
]

const GOVERNANCE_STATE_RESPONSE = {
  template_id: 'exec_brief',
  lifecycle_status: 'approved',
  default_version: '2.0.0',
  deprecated_versions: [],
}

const AUDIT_RESPONSE: unknown[] = []

const ANALYTICS_SUMMARY_RESPONSE = {
  template_id: 'exec_brief', date_window_days: 30,
  total_runs: 10, completed_runs: 8, failed_runs: 2, cancelled_runs: 0,
  failure_rate: 0.2,
}
const ANALYTICS_VERSIONS_RESPONSE = {
  template_id: 'exec_brief', date_window_days: 30, versions: [],
}
const ANALYTICS_TREND_RESPONSE = {
  template_id: 'exec_brief', date_window_days: 30, trend: [],
}

/** Build the 9-response queue used by the updated TemplateDetailPage. */
function makeFullQueue(runs = RUNS_RESPONSE) {
  return [
    ok(DETAIL_RESPONSE),               // [0] fetchTemplateDetail
    ok(VERSIONS_RESPONSE),             // [1] fetchTemplateVersions (useTemplateDetail)
    ok(runs),                          // [2] fetchTemplateRuns
    ok(VERSIONS_WITH_GOV_RESPONSE),    // [3] fetchTemplateVersionsWithGovernance
    ok(GOVERNANCE_STATE_RESPONSE),     // [4] fetchGovernanceState
    ok(AUDIT_RESPONSE),                // [5] fetchGovernanceAudit
    ok(ANALYTICS_SUMMARY_RESPONSE),    // [6] fetchTemplateAnalyticsSummary
    ok(ANALYTICS_VERSIONS_RESPONSE),   // [7] fetchTemplateAnalyticsVersions
    ok(ANALYTICS_TREND_RESPONSE),      // [8] fetchTemplateAnalyticsTrend
  ]
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
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('renders template name after loading', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Executive Brief')).toBeInTheDocument()
    })
  })

  it('shows template ID', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('exec_brief')).toBeInTheDocument()
    })
  })

  it('shows owner and description', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Analytics Services')).toBeInTheDocument()
      expect(screen.getByText('Concise deck for leadership.')).toBeInTheDocument()
    })
  })

  it('shows lifecycle status badge', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      const badges = screen.getAllByText('approved')
      expect(badges.length).toBeGreaterThan(0)
    })
  })

  it('shows version history table', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      // Both versions appear (possibly multiple times across metadata + tables)
      expect(screen.getAllByText('1.0.0').length).toBeGreaterThan(0)
      expect(screen.getAllByText('2.0.0').length).toBeGreaterThan(0)
    })
  })

  it('shows revision hashes in version table', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('ab12cd34ef56ab12')).toBeInTheDocument()
    })
  })

  it('shows usage card with runs count', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Usage (last 30 days)')).toBeInTheDocument()
    })
  })

  it('shows empty usage when no runs', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue(EMPTY_RUNS_RESPONSE)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No runs in the last 30 days.')).toBeInTheDocument()
    })
  })

  it('shows back link to templates', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
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
      ok(VERSIONS_WITH_GOV_RESPONSE),
      ok(GOVERNANCE_STATE_RESPONSE),
      ok(AUDIT_RESPONSE),
      ok(ANALYTICS_SUMMARY_RESPONSE),
      ok(ANALYTICS_VERSIONS_RESPONSE),
      ok(ANALYTICS_TREND_RESPONSE),
    ]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('shows Version History section heading', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeInTheDocument()
    })
  })

  it('shows governance actions section', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Governance Actions' })).toBeInTheDocument()
    })
  })

  it('shows default version badge on promoted version', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText('default version')).toBeInTheDocument()
    })
  })

  it('shows audit trail section', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Governance Audit Trail' })).toBeInTheDocument()
    })
  })
})
