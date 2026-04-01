/**
 * Integration tests for version promotion/deprecation/lifecycle UI
 * via the full TemplateDetailPage — Phase 8 Stage 3.
 *
 * Fetch call order per render (6 calls):
 *  [0] fetchTemplateDetail
 *  [1] fetchTemplateVersions  (useTemplateDetail, unused in render but still called)
 *  [2] fetchTemplateRuns
 *  [3] fetchTemplateVersionsWithGovernance
 *  [4] fetchGovernanceState
 *  [5] fetchGovernanceAudit
 *
 * After a mutation (promote/deprecate/lifecycle), useGovernance re-fetches
 * calls [3], [4], [5] again.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TemplateDetailPage } from '../pages/TemplateDetailPage'
import type { GovernanceState, TemplateVersionWithGovernance } from '../types'

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

const DETAIL = {
  template_id: 'exec_brief',
  name: 'Executive Brief',
  description: null,
  owner: null,
  lifecycle_status: 'approved',
  versions: ['1.0.0', '2.0.0'],
}

const VERSIONS_PLAIN = [
  { version: '1.0.0', template_revision_hash: 'ab12', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional' },
  { version: '2.0.0', template_revision_hash: 'cd34', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional' },
]

const RUNS_EMPTY = { template_id: 'exec_brief', runs: [], total: 0, limit: 50, offset: 0 }

const VERSIONS_GOV_NO_DEFAULT = [
  { version: '1.0.0', template_revision_hash: 'ab12', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional', is_default: false, deprecated_at: null, deprecation_reason: null, promotion_timestamp: null },
  { version: '2.0.0', template_revision_hash: 'cd34', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional', is_default: false, deprecated_at: null, deprecation_reason: null, promotion_timestamp: null },
]

const VERSIONS_GOV_2_DEFAULT = [
  { version: '1.0.0', template_revision_hash: 'ab12', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional', is_default: false, deprecated_at: null, deprecation_reason: null, promotion_timestamp: null },
  { version: '2.0.0', template_revision_hash: 'cd34', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional', is_default: true, deprecated_at: null, deprecation_reason: null, promotion_timestamp: '2026-03-10T00:00:00Z' },
]

const VERSIONS_GOV_1_DEPRECATED = [
  { version: '1.0.0', template_revision_hash: 'ab12', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional', is_default: false, deprecated_at: '2026-03-11T00:00:00Z', deprecation_reason: 'old', promotion_timestamp: null },
  { version: '2.0.0', template_revision_hash: 'cd34', template_path: null, playbook_path: null, input_contract_version: null, ai_mode: 'optional', is_default: false, deprecated_at: null, deprecation_reason: null, promotion_timestamp: null },
]

const GOV_STATE_NO_DEFAULT: GovernanceState = { template_id: 'exec_brief', lifecycle_status: 'approved', default_version: null, deprecated_versions: [] }
const GOV_STATE_2_DEFAULT: GovernanceState = { template_id: 'exec_brief', lifecycle_status: 'approved', default_version: '2.0.0', deprecated_versions: [] }

const AUDIT_EMPTY: unknown[] = []
const AUDIT_PROMOTE = [
  { event_type: 'template_version_promoted', template_id: 'exec_brief', template_version: '2.0.0', actor: 'alice', reason: 'ready', timestamp: '2026-03-10T00:00:00Z', metadata: null },
]
const AUDIT_DEPRECATE = [
  { event_type: 'template_version_deprecated', template_id: 'exec_brief', template_version: '1.0.0', actor: null, reason: 'old', timestamp: '2026-03-11T00:00:00Z', metadata: null },
]
const AUDIT_LIFECYCLE = [
  { event_type: 'template_lifecycle_changed', template_id: 'exec_brief', template_version: null, actor: null, reason: null, timestamp: '2026-03-12T00:00:00Z', metadata: null },
]

// Analytics responses (Phase 8 Analytics) — appended to every initial-load queue
const ANALYTICS_SUMMARY = { template_id: 'exec_brief', date_window_days: 30, total_runs: 0, completed_runs: 0, failed_runs: 0, cancelled_runs: 0, failure_rate: null }
const ANALYTICS_VERSIONS = { template_id: 'exec_brief', date_window_days: 30, versions: [] }
const ANALYTICS_TREND = { template_id: 'exec_brief', date_window_days: 30, trend: [] }

const PROMOTE_RESPONSE = {
  template_id: 'exec_brief', version: '2.0.0', action: 'promoted', accepted: true,
  message: 'Version 2.0.0 is now the default for exec_brief.', previous_default: null,
}

const DEPRECATE_RESPONSE = {
  template_id: 'exec_brief', version: '1.0.0', action: 'deprecated', accepted: true,
  message: 'Version 1.0.0 of exec_brief is now deprecated.', previous_default: null,
}

const LIFECYCLE_RESPONSE = {
  template_id: 'exec_brief', action: 'lifecycle_changed', accepted: true,
  message: "Lifecycle of exec_brief changed from 'approved' to 'deprecated'.", previous_default: null,
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

// ---------------------------------------------------------------------------
// Initial page load with governance state
// ---------------------------------------------------------------------------

function initialLoad(govVersions: TemplateVersionWithGovernance[] = VERSIONS_GOV_NO_DEFAULT, govState: GovernanceState = GOV_STATE_NO_DEFAULT, audit: unknown[] = AUDIT_EMPTY) {
  return [
    ok(DETAIL), ok(VERSIONS_PLAIN), ok(RUNS_EMPTY),
    ok(govVersions), ok(govState), ok(audit),
    ok(ANALYTICS_SUMMARY), ok(ANALYTICS_VERSIONS), ok(ANALYTICS_TREND),
  ]
}

describe('TemplateDetailPage — governance section', () => {
  it('shows Governance Actions section after load', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(initialLoad()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'Governance Actions' })).toBeInTheDocument()
    })
  })

  it('shows "default" badge when version is pinned default', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(initialLoad(VERSIONS_GOV_2_DEFAULT, GOV_STATE_2_DEFAULT)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText('default version')).toBeInTheDocument()
    })
  })

  it('shows "deprecated" badge on deprecated version', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(initialLoad(VERSIONS_GOV_1_DEPRECATED)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByLabelText('deprecated version')).toBeInTheDocument()
    })
  })

  it('shows empty audit trail message initially', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(initialLoad()))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No governance events recorded.')).toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// Promote action
// ---------------------------------------------------------------------------

describe('TemplateDetailPage — promote version', () => {
  it('calls promote API and re-renders with default badge', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      // Initial load (9 calls)
      ...initialLoad(),
      // After promote POST
      ok(PROMOTE_RESPONSE),        // [9] promote API call
      // Governance re-fetch (3 calls)
      ok(VERSIONS_GOV_2_DEFAULT),  // [10]
      ok(GOV_STATE_2_DEFAULT),     // [11]
      ok(AUDIT_PROMOTE),           // [12]
    ]))

    renderPage()

    await waitFor(() => screen.getByRole('form', { name: 'Promote version' }))

    const select = screen.getByLabelText('Version', { selector: '#promote-version-exec_brief' })
    fireEvent.change(select, { target: { value: '2.0.0' } })
    fireEvent.submit(screen.getByRole('form', { name: 'Promote version' }))

    await waitFor(() => {
      expect(screen.getByLabelText('default version')).toBeInTheDocument()
    })
  })

  it('shows audit event after promote', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ...initialLoad(),
      ok(PROMOTE_RESPONSE),
      ok(VERSIONS_GOV_2_DEFAULT), ok(GOV_STATE_2_DEFAULT), ok(AUDIT_PROMOTE),
    ]))

    renderPage()
    await waitFor(() => screen.getByRole('form', { name: 'Promote version' }))

    const select = screen.getByLabelText('Version', { selector: '#promote-version-exec_brief' })
    fireEvent.change(select, { target: { value: '2.0.0' } })
    fireEvent.submit(screen.getByRole('form', { name: 'Promote version' }))

    await waitFor(() => {
      expect(screen.getByText('template_version_promoted')).toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// Deprecate action
// ---------------------------------------------------------------------------

describe('TemplateDetailPage — deprecate version', () => {
  it('calls deprecate API and re-renders with deprecated badge', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ...initialLoad(),
      ok(DEPRECATE_RESPONSE),
      ok(VERSIONS_GOV_1_DEPRECATED), ok(GOV_STATE_NO_DEFAULT), ok(AUDIT_DEPRECATE),
    ]))

    renderPage()
    await waitFor(() => screen.getByRole('form', { name: 'Deprecate version' }))

    const select = screen.getByLabelText('Version', { selector: '#deprecate-version-exec_brief' })
    fireEvent.change(select, { target: { value: '1.0.0' } })

    const reasonInput = screen.getByLabelText('Reason *', { selector: '#deprecate-reason-exec_brief' })
    fireEvent.change(reasonInput, { target: { value: 'old' } })

    fireEvent.submit(screen.getByRole('form', { name: 'Deprecate version' }))

    await waitFor(() => {
      expect(screen.getByLabelText('deprecated version')).toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// Lifecycle change action
// ---------------------------------------------------------------------------

describe('TemplateDetailPage — lifecycle change', () => {
  it('calls lifecycle API and re-renders with new lifecycle badge', async () => {
    const GOV_AFTER = { ...GOV_STATE_NO_DEFAULT, lifecycle_status: 'deprecated' }

    vi.stubGlobal('fetch', makeFetchQueue([
      ...initialLoad(),
      ok(LIFECYCLE_RESPONSE),
      ok(VERSIONS_GOV_NO_DEFAULT), ok(GOV_AFTER), ok(AUDIT_LIFECYCLE),
    ]))

    renderPage()
    await waitFor(() => screen.getByRole('form', { name: 'Change lifecycle' }))

    const select = screen.getByLabelText('New Status', { selector: '#lifecycle-status-exec_brief' })
    fireEvent.change(select, { target: { value: 'deprecated' } })
    fireEvent.submit(screen.getByRole('form', { name: 'Change lifecycle' }))

    await waitFor(() => {
      expect(screen.getAllByText('deprecated').length).toBeGreaterThan(0)
    })
  })

  it('shows lifecycle audit event after change', async () => {
    const GOV_AFTER = { ...GOV_STATE_NO_DEFAULT, lifecycle_status: 'deprecated' }

    vi.stubGlobal('fetch', makeFetchQueue([
      ...initialLoad(),
      ok(LIFECYCLE_RESPONSE),
      ok(VERSIONS_GOV_NO_DEFAULT), ok(GOV_AFTER), ok(AUDIT_LIFECYCLE),
    ]))

    renderPage()
    await waitFor(() => screen.getByRole('form', { name: 'Change lifecycle' }))

    const select = screen.getByLabelText('New Status', { selector: '#lifecycle-status-exec_brief' })
    fireEvent.change(select, { target: { value: 'deprecated' } })
    fireEvent.submit(screen.getByRole('form', { name: 'Change lifecycle' }))

    await waitFor(() => {
      expect(screen.getByText('template_lifecycle_changed')).toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

describe('TemplateDetailPage — governance error handling', () => {
  it('shows action error message when API returns error', async () => {
    vi.stubGlobal('fetch', makeFetchQueue([
      ...initialLoad(),
      err(422, { detail: 'Cannot promote deprecated version' }),
      // Governance re-fetch after failure
      ok(VERSIONS_GOV_NO_DEFAULT), ok(GOV_STATE_NO_DEFAULT), ok(AUDIT_EMPTY),
    ]))

    renderPage()
    await waitFor(() => screen.getByRole('form', { name: 'Promote version' }))

    const select = screen.getByLabelText('Version', { selector: '#promote-version-exec_brief' })
    fireEvent.change(select, { target: { value: '2.0.0' } })
    fireEvent.submit(screen.getByRole('form', { name: 'Promote version' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
