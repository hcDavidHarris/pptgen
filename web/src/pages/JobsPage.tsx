import { useState } from 'react'
import { useJobs } from '../hooks/useJobs'
import { JobsTable } from '../components/JobsTable'
import { ErrorState } from '../components/ErrorState'
import { EmptyState } from '../components/EmptyState'

type StatusFilter = '' | 'queued' | 'running' | 'failed' | 'cancelled'

const FILTERS: { label: string; value: StatusFilter }[] = [
  { label: 'All', value: '' },
  { label: 'Queued', value: 'queued' },
  { label: 'Running', value: 'running' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' },
]

export function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('')
  const { jobs, loading, error, refresh } = useJobs({
    limit: 50,
    status: statusFilter || undefined,
  })

  return (
    <main className="page-container">
      <div className="page-toolbar">
        <h2>Jobs</h2>
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

      <div className="jobs-filter">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            className={`btn btn--small ${statusFilter === f.value ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => setStatusFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <ErrorState error={error} onRetry={refresh} />}

      {!error && !loading && jobs.length === 0 && (
        <EmptyState message="No jobs found." />
      )}

      {!error && jobs.length > 0 && (
        <JobsTable jobs={jobs} onRefresh={refresh} />
      )}
    </main>
  )
}
