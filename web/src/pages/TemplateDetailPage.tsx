import { useParams, NavLink } from 'react-router-dom'
import { useTemplateDetail } from '../hooks/useTemplateDetail'
import { useTemplateRuns } from '../hooks/useTemplateRuns'
import { TemplateVersionList } from '../components/TemplateVersionList'
import { TemplateUsageCard } from '../components/TemplateUsageCard'
import { ErrorState } from '../components/ErrorState'

export function TemplateDetailPage() {
  const { templateId } = useParams<{ templateId: string }>()
  const id = templateId ?? ''

  const { template, versions, loading, error } = useTemplateDetail(id)
  const { runs, loading: runsLoading, error: runsError } = useTemplateRuns(id, { days: 30, limit: 50 })

  if (loading) {
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

  return (
    <main className="page-container">
      <NavLink to="/templates" className="run-detail__back">← Back to Templates</NavLink>

      <div className="template-detail__header">
        <h2>{template.name}</h2>
        <span className={`lifecycle-badge lifecycle-badge--${template.lifecycle_status}`}>
          {template.lifecycle_status}
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
            <dd>{template.lifecycle_status}</dd>
          </div>
          <div className="run-summary-card__field">
            <dt>Versions</dt>
            <dd>{template.versions.join(', ') || '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="template-detail__versions card">
        <h3>Version History</h3>
        <TemplateVersionList versions={versions} />
      </section>

      <TemplateUsageCard runs={runs} loading={runsLoading} error={runsError} />
    </main>
  )
}
