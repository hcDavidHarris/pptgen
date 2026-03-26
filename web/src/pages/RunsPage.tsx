import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRuns } from '../hooks/useRuns'
import { useRunStats } from '../hooks/useRunStats'
import { useSystemHealth } from '../hooks/useSystemHealth'
import { RunTable } from '../components/RunTable'
import { RunStatsCard } from '../components/RunStatsCard'
import { SystemHealthCard } from '../components/SystemHealthCard'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'

export function RunsPage() {
  const { runs, loading, error, refresh } = useRuns({ limit: 50 })
  const { stats, loading: statsLoading, error: statsError } = useRunStats('24h')
  const { health, loading: healthLoading, error: healthError } = useSystemHealth()
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const navigate = useNavigate()

  const handleToggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  function handleCompare() {
    const [a, b] = Array.from(selectedIds)
    navigate(`/runs/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`)
  }

  const canCompare = selectedIds.size === 2

  return (
    <main className="page-container">
      <div className="page-toolbar">
        <h2>Runs</h2>
        <div className="page-toolbar__actions">
          {canCompare && (
            <button
              type="button"
              className="btn btn--primary btn--small"
              onClick={handleCompare}
            >
              Compare selected
            </button>
          )}
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

      <div className="runs-overview-grid">
        <RunStatsCard stats={stats} loading={statsLoading} error={statsError} window="24h" />
        <SystemHealthCard health={health} loading={healthLoading} error={healthError} />
      </div>

      {error && <ErrorState error={error} onRetry={refresh} />}

      {!error && !loading && runs.length === 0 && (
        <EmptyState message="No runs found. Generate a presentation to see runs here." />
      )}

      {!error && runs.length > 0 && (
        <RunTable
          runs={runs}
          selectedIds={selectedIds}
          onToggleSelect={handleToggleSelect}
        />
      )}
    </main>
  )
}
