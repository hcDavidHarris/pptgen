import { useTemplates } from '../hooks/useTemplates'
import { TemplateTable } from '../components/TemplateTable'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'

export function TemplatesPage() {
  const { templates, loading, error, refresh } = useTemplates()

  return (
    <main className="page-container">
      <div className="page-toolbar">
        <h2>Templates</h2>
        <div className="page-toolbar__actions">
          <button
            type="button"
            className="btn btn--secondary btn--small"
            onClick={refresh}
            disabled={loading}
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      {loading && <p aria-busy="true">Loading templates…</p>}

      {error && <ErrorState error={error} onRetry={refresh} />}

      {!loading && !error && templates.length === 0 && (
        <EmptyState message="No templates registered." />
      )}

      {!loading && !error && templates.length > 0 && (
        <TemplateTable templates={templates} />
      )}
    </main>
  )
}
