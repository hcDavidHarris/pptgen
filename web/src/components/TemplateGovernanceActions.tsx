import { useState } from 'react'
import type { GovernanceAuditEvent, GovernanceState, TemplateVersionWithGovernance } from '../types'

interface GovernanceActionsProps {
  templateId: string
  governance: GovernanceState
  versions: TemplateVersionWithGovernance[]
  actionPending: boolean
  actionError: Error | null
  onPromote: (version: string, reason: string, actor: string) => void
  onDeprecate: (version: string, reason: string, actor: string) => void
  onLifecycleChange: (lifecycle: string, reason: string, actor: string) => void
}

const LIFECYCLE_OPTIONS = ['draft', 'review', 'approved', 'deprecated']

export function TemplateGovernanceActions({
  templateId,
  governance,
  versions,
  actionPending,
  actionError,
  onPromote,
  onDeprecate,
  onLifecycleChange,
}: GovernanceActionsProps) {
  const [promoteVersion, setPromoteVersion] = useState('')
  const [promoteReason, setPromoteReason] = useState('')
  const [promoteActor, setPromoteActor] = useState('')

  const [deprecateVersion, setDeprecateVersion] = useState('')
  const [deprecateReason, setDeprecateReason] = useState('')
  const [deprecateActor, setDeprecateActor] = useState('')

  const [lifecycleStatus, setLifecycleStatus] = useState('')
  const [lifecycleReason, setLifecycleReason] = useState('')
  const [lifecycleActor, setLifecycleActor] = useState('')

  const promotableVersions = versions.filter((v) => !v.deprecated_at)
  const deprecatableVersions = versions.filter(
    (v) => !v.deprecated_at && versions.filter((w) => !w.deprecated_at).length > 1,
  )

  function handlePromote(e: React.FormEvent) {
    e.preventDefault()
    if (!promoteVersion) return
    onPromote(promoteVersion, promoteReason, promoteActor)
    setPromoteReason('')
    setPromoteActor('')
  }

  function handleDeprecate(e: React.FormEvent) {
    e.preventDefault()
    if (!deprecateVersion || !deprecateReason) return
    onDeprecate(deprecateVersion, deprecateReason, deprecateActor)
    setDeprecateReason('')
    setDeprecateActor('')
  }

  function handleLifecycle(e: React.FormEvent) {
    e.preventDefault()
    if (!lifecycleStatus) return
    onLifecycleChange(lifecycleStatus, lifecycleReason, lifecycleActor)
    setLifecycleReason('')
    setLifecycleActor('')
  }

  return (
    <section className="template-governance-actions card" aria-label="Governance Actions">
      <h3>Governance Actions</h3>

      {actionError && (
        <p className="template-governance-actions__error" role="alert">
          {actionError.message}
        </p>
      )}

      <div className="template-governance-actions__forms">
        {/* Promote version */}
        <form
          className="template-governance-actions__form"
          onSubmit={handlePromote}
          aria-label="Promote version"
        >
          <h4>Promote Version</h4>
          <label htmlFor={`promote-version-${templateId}`}>Version</label>
          <select
            id={`promote-version-${templateId}`}
            value={promoteVersion}
            onChange={(e) => setPromoteVersion(e.target.value)}
            disabled={actionPending || promotableVersions.length === 0}
          >
            <option value="">Select version…</option>
            {promotableVersions.map((v) => (
              <option key={v.version} value={v.version}>
                {v.version}{v.is_default ? ' (current default)' : ''}
              </option>
            ))}
          </select>
          <label htmlFor={`promote-reason-${templateId}`}>Reason (optional)</label>
          <input
            id={`promote-reason-${templateId}`}
            type="text"
            placeholder="e.g. stable release"
            value={promoteReason}
            onChange={(e) => setPromoteReason(e.target.value)}
            disabled={actionPending}
          />
          <label htmlFor={`promote-actor-${templateId}`}>Actor (optional)</label>
          <input
            id={`promote-actor-${templateId}`}
            type="text"
            placeholder="e.g. alice"
            value={promoteActor}
            onChange={(e) => setPromoteActor(e.target.value)}
            disabled={actionPending}
          />
          <button type="submit" disabled={actionPending || !promoteVersion}>
            {actionPending ? 'Working…' : 'Promote'}
          </button>
        </form>

        {/* Deprecate version */}
        <form
          className="template-governance-actions__form"
          onSubmit={handleDeprecate}
          aria-label="Deprecate version"
        >
          <h4>Deprecate Version</h4>
          <label htmlFor={`deprecate-version-${templateId}`}>Version</label>
          <select
            id={`deprecate-version-${templateId}`}
            value={deprecateVersion}
            onChange={(e) => setDeprecateVersion(e.target.value)}
            disabled={actionPending || deprecatableVersions.length === 0}
          >
            <option value="">Select version…</option>
            {deprecatableVersions.map((v) => (
              <option key={v.version} value={v.version}>{v.version}</option>
            ))}
          </select>
          <label htmlFor={`deprecate-reason-${templateId}`}>Reason *</label>
          <input
            id={`deprecate-reason-${templateId}`}
            type="text"
            placeholder="e.g. superseded by 2.0.0"
            value={deprecateReason}
            onChange={(e) => setDeprecateReason(e.target.value)}
            disabled={actionPending}
            required
          />
          <label htmlFor={`deprecate-actor-${templateId}`}>Actor (optional)</label>
          <input
            id={`deprecate-actor-${templateId}`}
            type="text"
            placeholder="e.g. alice"
            value={deprecateActor}
            onChange={(e) => setDeprecateActor(e.target.value)}
            disabled={actionPending}
          />
          <button type="submit" disabled={actionPending || !deprecateVersion || !deprecateReason}>
            {actionPending ? 'Working…' : 'Deprecate'}
          </button>
        </form>

        {/* Lifecycle change */}
        <form
          className="template-governance-actions__form"
          onSubmit={handleLifecycle}
          aria-label="Change lifecycle"
        >
          <h4>Change Lifecycle</h4>
          <p className="template-governance-actions__current-lifecycle">
            Current: <span className={`lifecycle-badge lifecycle-badge--${governance.lifecycle_status}`}>
              {governance.lifecycle_status}
            </span>
          </p>
          <label htmlFor={`lifecycle-status-${templateId}`}>New Status</label>
          <select
            id={`lifecycle-status-${templateId}`}
            value={lifecycleStatus}
            onChange={(e) => setLifecycleStatus(e.target.value)}
            disabled={actionPending}
          >
            <option value="">Select status…</option>
            {LIFECYCLE_OPTIONS.filter((s) => s !== governance.lifecycle_status).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <label htmlFor={`lifecycle-reason-${templateId}`}>Reason (optional)</label>
          <input
            id={`lifecycle-reason-${templateId}`}
            type="text"
            placeholder="e.g. ready for production"
            value={lifecycleReason}
            onChange={(e) => setLifecycleReason(e.target.value)}
            disabled={actionPending}
          />
          <label htmlFor={`lifecycle-actor-${templateId}`}>Actor (optional)</label>
          <input
            id={`lifecycle-actor-${templateId}`}
            type="text"
            placeholder="e.g. alice"
            value={lifecycleActor}
            onChange={(e) => setLifecycleActor(e.target.value)}
            disabled={actionPending}
          />
          <button type="submit" disabled={actionPending || !lifecycleStatus}>
            {actionPending ? 'Working…' : 'Change Lifecycle'}
          </button>
        </form>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Governance audit trail
// ---------------------------------------------------------------------------

interface AuditTrailProps {
  events: GovernanceAuditEvent[]
}

export function GovernanceAuditTrail({ events }: AuditTrailProps) {
  if (events.length === 0) {
    return (
      <section className="governance-audit card" aria-label="Governance Audit Trail">
        <h3>Audit Trail</h3>
        <p className="governance-audit__empty">No governance events recorded.</p>
      </section>
    )
  }

  return (
    <section className="governance-audit card" aria-label="Governance Audit Trail">
      <h3>Audit Trail</h3>
      <table className="governance-audit__table">
        <thead>
          <tr>
            <th scope="col">Event</th>
            <th scope="col">Version</th>
            <th scope="col">Actor</th>
            <th scope="col">Reason</th>
            <th scope="col">Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {events.map((evt, i) => (
            <tr key={i} className="governance-audit__row">
              <td><code>{evt.event_type}</code></td>
              <td>{evt.template_version ?? '—'}</td>
              <td>{evt.actor ?? '—'}</td>
              <td>{evt.reason ?? '—'}</td>
              <td>{new Date(evt.timestamp).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
