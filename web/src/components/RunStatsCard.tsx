import type { RunStats } from '../types'

interface Props {
  stats: RunStats | null
  loading: boolean
  error: Error | null
  window?: string
}

const WINDOW_LABELS: Record<string, string> = {
  '1h': '1 hour',
  '24h': '24 hours',
  '7d': '7 days',
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`
  return `${(ms / 60_000).toFixed(1)} min`
}

export function RunStatsCard({ stats, loading, error, window = '24h' }: Props) {
  if (loading) {
    return (
      <div className="run-stats-card run-stats-card--loading" aria-busy="true">
        <span>Loading stats…</span>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="run-stats-card run-stats-card--unavailable">
        Stats unavailable
      </div>
    )
  }

  const windowLabel = WINDOW_LABELS[window] ?? window

  return (
    <div className="run-stats-card" aria-label="Run summary stats">
      <p className="run-stats-card__window">Last {windowLabel}</p>
      <dl className="run-stats-card__grid">
        <div className="run-stats-card__stat">
          <dt>Total</dt>
          <dd>{stats.total_runs}</dd>
        </div>
        <div className="run-stats-card__stat">
          <dt>Success rate</dt>
          <dd>{stats.success_rate != null ? `${stats.success_rate}%` : '—'}</dd>
        </div>
        <div className={`run-stats-card__stat${stats.failed_runs > 0 ? ' run-stats-card__stat--warn' : ''}`}>
          <dt>Failed</dt>
          <dd>{stats.failed_runs}</dd>
        </div>
        <div className="run-stats-card__stat">
          <dt>Avg duration</dt>
          <dd>{stats.avg_duration_ms != null ? formatDuration(stats.avg_duration_ms) : '—'}</dd>
        </div>
        {stats.running_runs > 0 && (
          <div className="run-stats-card__stat run-stats-card__stat--running">
            <dt>Running</dt>
            <dd>{stats.running_runs}</dd>
          </div>
        )}
      </dl>
    </div>
  )
}
