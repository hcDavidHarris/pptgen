import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TemplateGovernanceActions, GovernanceAuditTrail } from '../components/TemplateGovernanceActions'
import type { GovernanceAuditEvent, GovernanceState, TemplateVersionWithGovernance } from '../types'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const GOVERNANCE_STATE: GovernanceState = {
  template_id: 'exec_brief',
  lifecycle_status: 'approved',
  default_version: '2.0.0',
  deprecated_versions: ['1.0.0'],
}

const VERSIONS: TemplateVersionWithGovernance[] = [
  {
    version: '1.0.0',
    template_revision_hash: 'ab12cd34ef56ab12',
    template_path: null,
    playbook_path: null,
    input_contract_version: null,
    ai_mode: 'optional',
    is_default: false,
    deprecated_at: '2026-03-01T00:00:00Z',
    deprecation_reason: 'superseded',
    promotion_timestamp: null,
  },
  {
    version: '2.0.0',
    template_revision_hash: 'cd34ef56ab12cd34',
    template_path: null,
    playbook_path: null,
    input_contract_version: null,
    ai_mode: 'optional',
    is_default: true,
    deprecated_at: null,
    deprecation_reason: null,
    promotion_timestamp: '2026-03-10T00:00:00Z',
  },
]

const AUDIT_EVENTS: GovernanceAuditEvent[] = [
  {
    event_type: 'template_version_promoted',
    template_id: 'exec_brief',
    template_version: '2.0.0',
    actor: 'alice',
    reason: 'stable release',
    timestamp: '2026-03-10T00:00:00Z',
    metadata: null,
  },
  {
    event_type: 'template_version_deprecated',
    template_id: 'exec_brief',
    template_version: '1.0.0',
    actor: 'bob',
    reason: 'superseded',
    timestamp: '2026-03-11T00:00:00Z',
    metadata: null,
  },
]

function renderActions({
  governance = GOVERNANCE_STATE,
  versions = VERSIONS,
  actionPending = false,
  actionError = null as Error | null,
  onPromote = vi.fn(),
  onDeprecate = vi.fn(),
  onLifecycleChange = vi.fn(),
} = {}) {
  return render(
    <TemplateGovernanceActions
      templateId="exec_brief"
      governance={governance}
      versions={versions}
      actionPending={actionPending}
      actionError={actionError}
      onPromote={onPromote}
      onDeprecate={onDeprecate}
      onLifecycleChange={onLifecycleChange}
    />
  )
}

// ---------------------------------------------------------------------------
// TemplateGovernanceActions
// ---------------------------------------------------------------------------

describe('TemplateGovernanceActions', () => {
  it('renders all three forms', () => {
    renderActions()
    expect(screen.getByRole('form', { name: 'Promote version' })).toBeInTheDocument()
    expect(screen.getByRole('form', { name: 'Deprecate version' })).toBeInTheDocument()
    expect(screen.getByRole('form', { name: 'Change lifecycle' })).toBeInTheDocument()
  })

  it('shows current lifecycle status', () => {
    renderActions()
    expect(screen.getByText('approved')).toBeInTheDocument()
  })

  it('calls onPromote with version, reason, actor when form submitted', () => {
    const onPromote = vi.fn()
    renderActions({ onPromote })

    const select = screen.getByLabelText('Version', { selector: '#promote-version-exec_brief' })
    fireEvent.change(select, { target: { value: '2.0.0' } })

    const reasonInput = screen.getByLabelText('Reason (optional)', { selector: '#promote-reason-exec_brief' })
    fireEvent.change(reasonInput, { target: { value: 'stable release' } })

    fireEvent.submit(screen.getByRole('form', { name: 'Promote version' }))

    expect(onPromote).toHaveBeenCalledWith('2.0.0', 'stable release', '')
  })

  it('calls onDeprecate with version, reason, actor when form submitted', () => {
    const onDeprecate = vi.fn()
    // Two non-deprecated versions so deprecation is allowed
    const twoActiveVersions: TemplateVersionWithGovernance[] = [
      { ...VERSIONS[1] },
      {
        version: '3.0.0',
        template_revision_hash: 'ef56ab12cd34ef56',
        template_path: null,
        playbook_path: null,
        input_contract_version: null,
        ai_mode: 'optional',
        is_default: false,
        deprecated_at: null,
        deprecation_reason: null,
        promotion_timestamp: null,
      },
    ]
    renderActions({ onDeprecate, versions: twoActiveVersions })

    const select = screen.getByLabelText('Version', { selector: '#deprecate-version-exec_brief' })
    fireEvent.change(select, { target: { value: '3.0.0' } })

    const reasonInput = screen.getByLabelText('Reason *', { selector: '#deprecate-reason-exec_brief' })
    fireEvent.change(reasonInput, { target: { value: 'old release' } })

    fireEvent.submit(screen.getByRole('form', { name: 'Deprecate version' }))

    expect(onDeprecate).toHaveBeenCalledWith('3.0.0', 'old release', '')
  })

  it('calls onLifecycleChange with status, reason, actor when form submitted', () => {
    const onLifecycleChange = vi.fn()
    renderActions({ onLifecycleChange })

    const select = screen.getByLabelText('New Status', { selector: '#lifecycle-status-exec_brief' })
    fireEvent.change(select, { target: { value: 'deprecated' } })

    fireEvent.submit(screen.getByRole('form', { name: 'Change lifecycle' }))

    expect(onLifecycleChange).toHaveBeenCalledWith('deprecated', '', '')
  })

  it('promote button is disabled when no version selected', () => {
    renderActions()
    expect(screen.getByText('Promote')).toBeDisabled()
  })

  it('deprecate button is disabled when no version or reason entered', () => {
    // With two non-deprecated versions
    const twoActive: TemplateVersionWithGovernance[] = [
      { ...VERSIONS[1] },
      { ...VERSIONS[1], version: '3.0.0', is_default: false },
    ]
    renderActions({ versions: twoActive })
    expect(screen.getByText('Deprecate')).toBeDisabled()
  })

  it('lifecycle change button is disabled when no status selected', () => {
    renderActions()
    expect(screen.getByRole('button', { name: 'Change Lifecycle' })).toBeDisabled()
  })

  it('shows Working… on all buttons when actionPending is true', () => {
    renderActions({ actionPending: true })
    const workingButtons = screen.getAllByText('Working…')
    expect(workingButtons.length).toBe(3)
  })

  it('shows error message when actionError is set', () => {
    renderActions({ actionError: new Error('Promote failed: 422') })
    expect(screen.getByRole('alert')).toHaveTextContent('Promote failed: 422')
  })

  it('does not show error alert when actionError is null', () => {
    renderActions({ actionError: null })
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('lifecycle dropdown does not include current status', () => {
    renderActions()
    const select = screen.getByLabelText('New Status', { selector: '#lifecycle-status-exec_brief' })
    const options = Array.from((select as HTMLSelectElement).options).map((o) => o.value)
    expect(options).not.toContain('approved')
    expect(options).toContain('deprecated')
    expect(options).toContain('draft')
    expect(options).toContain('review')
  })

  it('shows only non-deprecated versions in promote dropdown', () => {
    renderActions()
    const select = screen.getByLabelText('Version', { selector: '#promote-version-exec_brief' })
    const options = Array.from((select as HTMLSelectElement).options).map((o) => o.value)
    expect(options).toContain('2.0.0')
    expect(options).not.toContain('1.0.0') // 1.0.0 is deprecated
  })
})

// ---------------------------------------------------------------------------
// GovernanceAuditTrail
// ---------------------------------------------------------------------------

describe('GovernanceAuditTrail', () => {
  it('shows empty message when no events', () => {
    render(<GovernanceAuditTrail events={[]} />)
    expect(screen.getByText('No governance events recorded.')).toBeInTheDocument()
  })

  it('renders audit event rows', () => {
    render(<GovernanceAuditTrail events={AUDIT_EVENTS} />)
    expect(screen.getByText('template_version_promoted')).toBeInTheDocument()
    expect(screen.getByText('template_version_deprecated')).toBeInTheDocument()
  })

  it('shows actor and reason columns', () => {
    render(<GovernanceAuditTrail events={AUDIT_EVENTS} />)
    expect(screen.getByText('alice')).toBeInTheDocument()
    expect(screen.getByText('stable release')).toBeInTheDocument()
    expect(screen.getByText('bob')).toBeInTheDocument()
    expect(screen.getByText('superseded')).toBeInTheDocument()
  })

  it('shows version column', () => {
    render(<GovernanceAuditTrail events={AUDIT_EVENTS} />)
    expect(screen.getAllByText('2.0.0').length).toBeGreaterThan(0)
    expect(screen.getAllByText('1.0.0').length).toBeGreaterThan(0)
  })

  it('renders the audit trail section heading', () => {
    render(<GovernanceAuditTrail events={AUDIT_EVENTS} />)
    expect(screen.getByText('Audit Trail')).toBeInTheDocument()
  })
})
