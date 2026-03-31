import { useParams, NavLink } from 'react-router-dom'
import { useTemplateDetail } from '../hooks/useTemplateDetail'
import { useTemplateRuns } from '../hooks/useTemplateRuns'
import { useGovernance } from '../hooks/useGovernance'
import { useTemplateAnalytics } from '../hooks/useTemplateAnalytics'
import { TemplateVersionList } from '../components/TemplateVersionList'
import { TemplateUsageCard } from '../components/TemplateUsageCard'
import { TemplateGovernanceActions, GovernanceAuditTrail } from '../components/TemplateGovernanceActions'
import { TemplateAnalyticsSection } from '../components/TemplateAnalyticsSection'
import { ErrorState } from '../components/ErrorState'

export function TemplateDetailPage() {
  const { templateId } = useParams<{ templateId: string }>()
  const id = templateId ?? ''

  const { template, loading, error } = useTemplateDetail(id)
  const { runs, loading: runsLoading, error: runsError } = useTemplateRuns(id, { days: 30, limit: 50 })
  const {
    versions,
    governance,
    audit,
    loading: govLoading,
    error: govError,
    actionPending,
    actionError,
    promote,
    deprecate,
    setLifecycle,
  } = useGovernance(id)
  const { summary: analyticsSummary, versions: analyticsVersions, trend: analyticsTrend, loading: analyticsLoading, error: analyticsError } = useTemplateAnalytics(id)

  if (loading || govLoading) {
    return (
      <main className="app-main">
        <p aria-busy="true">Loading template…</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="app-main">
        <NavLink to="/templates">← Back to Templates</NavLink>
        <ErrorState error={error} />
      </main>
    )
  }

  if (!template) return null

  const effectiveLifecycle = governance?.lifecycle_status ?? template.lifecycle_status

  function handlePromote(version: string, reason: string, actor: string) {
    promote(version, { reason: reason || undefined, actor: actor || undefined })
  }

  function handleDeprecate(version: string, reason: string, actor: string) {
    deprecate(version, { reason, actor: actor || undefined })
  }

  function handleLifecycleChange(lifecycle: string, reason: string, actor: string) {
    setLifecycle({ lifecycle_status: lifecycle, reason: reason || undefined, actor: actor || undefined })
  }

  return (
    <main className="page-container">
      <NavLink to="/templates" className="run-detail__back">← Back to Templates</NavLink>

      <div className="template-detail__header">
        <h2>{template.name}</h2>
        <span className={`lifecycle-badge lifecycle-badge--${effectiveLifecycle}`}>
          {effectiveLifecycle}
        </span>
      </div>

      <section className="template-detail__metadata card">
        <h3>Metadata</h3>
        <dl className="run-summary-card__fields">
          <div className="run-summary-card__field">
            <dt>Template ID</dt>
            <dd><code>{template.template_id}</code></dd>
          </div>
          <div className="run-summary-card__field">
            <dt>Owner</dt>
            <dd>{template.owner ?? '—'}</dd>
          </div>
          <div className="run-summary-card__field">
            <dt>Description</dt>
            <dd>{template.description ?? '—'}</dd>
          </div>
          <div className="run-summary-card__field">
            <dt>Lifecycle Status</dt>
            <dd>{effectiveLifecycle}</dd>
          </div>
          {governance?.default_version && (
            <div className="run-summary-card__field">
              <dt>Default Version</dt>
              <dd><code>{governance.default_version}</code></dd>
            </div>
          )}
          <div className="run-summary-card__field">
            <dt>Versions</dt>
            <dd>{template.versions.join(', ') || '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="template-detail__versions card">
        <h3>Version History</h3>
        <TemplateVersionList versions={versions.length > 0 ? versions : []} />
      </section>

      {governance && (
        <TemplateGovernanceActions
          templateId={id}
          governance={governance}
          versions={versions}
          actionPending={actionPending}
          actionError={actionError}
          onPromote={handlePromote}
          onDeprecate={handleDeprecate}
          onLifecycleChange={handleLifecycleChange}
        />
      )}

      {govError && (
        <section className="template-detail__gov-error card">
          <p role="alert">Governance unavailable: {govError.message}</p>
        </section>
      )}

      <GovernanceAuditTrail events={audit} />

      <TemplateAnalyticsSection
        summary={analyticsSummary}
        versions={analyticsVersions}
        trend={analyticsTrend}
        loading={analyticsLoading}
        error={analyticsError}
      />

      <TemplateUsageCard runs={runs} loading={runsLoading} error={runsError} />
    </main>
  )
}
