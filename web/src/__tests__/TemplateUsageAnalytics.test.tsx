import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TemplateDetailPage } from '../pages/TemplateDetailPage'
import { TemplateAnalyticsSection } from '../components/TemplateAnalyticsSection'
import type { TemplateUsageSummary, TemplateVersionUsageItem, TemplateUsageTrendItem } from '../types'

// ---------------------------------------------------------------------------
// Helpers
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

const SUMMARY: TemplateUsageSummary = {
  template_id: 'exec_brief',
  date_window_days: 30,
  total_runs: 84,
  completed_runs: 69,
  failed_runs: 15,
  cancelled_runs: 0,
  failure_rate: 0.1786,
}

const SUMMARY_ZERO: TemplateUsageSummary = {
  template_id: 'exec_brief',
  date_window_days: 30,
  total_runs: 0,
  completed_runs: 0,
  failed_runs: 0,
  cancelled_runs: 0,
  failure_rate: null,
}

const VERSIONS_USAGE: TemplateVersionUsageItem[] = [
  { template_version: '2.0.0', total_runs: 78, failed_runs: 14, failure_rate: 0.1795, first_seen_at: '2026-03-01T00:00:00Z', last_seen_at: '2026-03-26T00:00:00Z' },
  { template_version: '1.0.0', total_runs: 6, failed_runs: 1, failure_rate: 0.1667, first_seen_at: '2026-02-25T00:00:00Z', last_seen_at: '2026-03-02T00:00:00Z' },
]

const TREND: TemplateUsageTrendItem[] = [
  { date: '2026-03-24', template_version: '2.0.0', run_count: 5 },
  { date: '2026-03-25', template_version: '2.0.0', run_count: 8 },
  { date: '2026-03-26', template_version: '2.0.0', run_count: 3 },
]

// ---------------------------------------------------------------------------
// Standalone component tests
// ---------------------------------------------------------------------------

describe('TemplateAnalyticsSection', () => {
  it('renders loading state', () => {
    render(
      <TemplateAnalyticsSection
        summary={null} versions={[]} trend={[]}
        loading={true} error={null}
      />
    )
    expect(screen.getByText('Loading analytics…')).toBeInTheDocument()
  })

  it('renders error state', () => {
    render(
      <TemplateAnalyticsSection
        summary={null} versions={[]} trend={[]}
        loading={false} error={new Error('503 Service Unavailable')}
      />
    )
    expect(screen.getByRole('alert')).toHaveTextContent('503 Service Unavailable')
  })

  it('renders empty state when summary is null and not loading', () => {
    render(
      <TemplateAnalyticsSection
        summary={null} versions={[]} trend={[]}
        loading={false} error={null}
      />
    )
    expect(screen.getByText('No analytics data available.')).toBeInTheDocument()
  })

  it('renders summary values', () => {
    render(
      <TemplateAnalyticsSection
        summary={SUMMARY} versions={[]} trend={[]}
        loading={false} error={null}
      />
    )
    expect(screen.getByText('84')).toBeInTheDocument()   // total runs
    expect(screen.getByText('69')).toBeInTheDocument()   // completed
    expect(screen.getByText('15')).toBeInTheDocument()   // failed
    expect(screen.getByText('17.9%')).toBeInTheDocument() // failure rate
  })

  it('shows failure rate as — when null', () => {
    render(
      <TemplateAnalyticsSection
        summary={SUMMARY_ZERO} versions={[]} trend={[]}
        loading={false} error={null}
      />
    )
    // failure_rate is null → should show '—'
    const dds = screen.getAllByRole('definition')
    const rateEl = dds.find((el) => el.textContent === '—')
    expect(rateEl).toBeTruthy()
  })

  it('renders version usage table', () => {
    render(
      <TemplateAnalyticsSection
        summary={SUMMARY} versions={VERSIONS_USAGE} trend={[]}
        loading={false} error={null}
      />
    )
    expect(screen.getByText('2.0.0')).toBeInTheDocument()
    expect(screen.getByText('1.0.0')).toBeInTheDocument()
    expect(screen.getByText('78')).toBeInTheDocument()
    expect(screen.getByText('6')).toBeInTheDocument()
  })

  it('shows empty message when versions list is empty', () => {
    render(
      <TemplateAnalyticsSection
        summary={SUMMARY} versions={[]} trend={[]}
        loading={false} error={null}
      />
    )
    expect(screen.getByText('No version data in this window.')).toBeInTheDocument()
  })

  it('renders trend table', () => {
    render(
      <TemplateAnalyticsSection
        summary={SUMMARY} versions={[]} trend={TREND}
        loading={false} error={null}
      />
    )
    expect(screen.getByText('2026-03-24')).toBeInTheDocument()
    expect(screen.getByText('2026-03-25')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
  })

  it('shows empty message when trend is empty', () => {
    render(
      <TemplateAnalyticsSection
        summary={SUMMARY} versions={[]} trend={[]}
        loading={false} error={null}
      />
    )
    expect(screen.getByText('No trend data in this window.')).toBeInTheDocument()
  })

  it('renders section heading', () => {
    render(
      <TemplateAnalyticsSection
        summary={SUMMARY} versions={VERSIONS_USAGE} trend={TREND}
        loading={false} error={null}
      />
    )
    expect(screen.getByText('Usage Analytics')).toBeInTheDocument()
  })

  it('shows first/last seen dates in version table', () => {
    render(
      <TemplateAnalyticsSection
        summary={SUMMARY} versions={VERSIONS_USAGE} trend={[]}
        loading={false} error={null}
      />
    )
    expect(screen.getByText('2026-03-01')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Integration: TemplateDetailPage includes analytics
// ---------------------------------------------------------------------------

// Fetch call order (9 calls on load):
// [0] fetchTemplateDetail
// [1] fetchTemplateVersions (useTemplateDetail)
// [2] fetchTemplateRuns
// [3] fetchTemplateVersionsWithGovernance (useGovernance)
// [4] fetchGovernanceState
// [5] fetchGovernanceAudit
// [6] fetchTemplateAnalyticsSummary
// [7] fetchTemplateAnalyticsVersions
// [8] fetchTemplateAnalyticsTrend

const DETAIL = {
  template_id: 'exec_brief', name: 'Executive Brief', description: null,
  owner: null, lifecycle_status: 'approved', versions: ['1.0.0', '2.0.0'],
}
const VERSIONS_PLAIN = [
  { version: '1.0.0', template_revision_hash: 'ab12', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional' },
  { version: '2.0.0', template_revision_hash: 'cd34', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional' },
]
const RUNS_EMPTY = { template_id: 'exec_brief', runs: [], total: 0, limit: 50, offset: 0 }
const VERSIONS_GOV = VERSIONS_PLAIN.map((v) => ({ ...v, is_default: false, deprecated_at: null, deprecation_reason: null, promotion_timestamp: null }))
const GOV_STATE = { template_id: 'exec_brief', lifecycle_status: 'approved', default_version: null, deprecated_versions: [] }
const AUDIT_EMPTY: unknown[] = []
const VERSIONS_USAGE_RESP = { template_id: 'exec_brief', date_window_days: 30, versions: VERSIONS_USAGE }
const TREND_RESP = { template_id: 'exec_brief', date_window_days: 30, trend: TREND }

function makeFullQueue() {
  return [
    ok(DETAIL),            // [0]
    ok(VERSIONS_PLAIN),    // [1]
    ok(RUNS_EMPTY),        // [2]
    ok(VERSIONS_GOV),      // [3]
    ok(GOV_STATE),         // [4]
    ok(AUDIT_EMPTY),       // [5]
    ok(SUMMARY),           // [6]
    ok(VERSIONS_USAGE_RESP), // [7]
    ok(TREND_RESP),        // [8]
  ]
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/templates/exec_brief']}>
      <Routes>
        <Route path="/templates/:templateId" element={<TemplateDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('TemplateDetailPage — analytics section', () => {
  it('shows Usage Analytics section heading', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Usage Analytics')).toBeInTheDocument()
    })
  })

  it('shows summary total runs', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('84')).toBeInTheDocument()
    })
  })

  it('shows version table with 2.0.0', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      // 2.0.0 appears both in governance version table and analytics version table
      const matches = screen.getAllByText('2.0.0')
      expect(matches.length).toBeGreaterThan(0)
    })
  })

  it('shows trend date', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(makeFullQueue()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('2026-03-24')).toBeInTheDocument()
    })
  })

  it('shows error alert when analytics fetch fails', async () => {
    const queue = [
      ok(DETAIL),
      ok(VERSIONS_PLAIN),
      ok(RUNS_EMPTY),
      ok(VERSIONS_GOV),
      ok(GOV_STATE),
      ok(AUDIT_EMPTY),
      err(503, { detail: 'Run store unavailable' }),
      err(503, { detail: 'Run store unavailable' }),
      err(503, { detail: 'Run store unavailable' }),
    ]
    vi.stubGlobal('fetch', makeFetchQueue(queue))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
