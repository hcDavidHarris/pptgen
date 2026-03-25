import { useRuns } from '../hooks/useRuns'
import { RunTable } from '../components/RunTable'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'

export function RunsPage() {
  const { runs, loading, error, refresh } = useRuns({ limit: 50 })

  return (
    <main className="page-container">
      <div className="page-toolbar">
        <h2>Runs</h2>
        <button
          type="button"
          className="btn btn--secondary btn--small"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <ErrorState error={error} onRetry={refresh} />}

      {!error && !loading && runs.length === 0 && (
        <EmptyState message="No runs found. Generate a presentation to see runs here." />
      )}

      {!error && runs.length > 0 && (
        <RunTable runs={runs} />
      )}
    </main>
  )
}
