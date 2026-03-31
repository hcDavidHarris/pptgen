import type { SystemHealth } from '../types'

interface Props {
  health: SystemHealth | null
  loading: boolean
  error: Error | null
}

export function SystemHealthCard({ health, loading, error }: Props) {
  if (loading) {
    return (
      <div className="system-health-card system-health-card--loading" aria-busy="true">
        <span>Loading…</span>
      </div>
    )
  }

  if (error || !health) {
    return (
      <div className="system-health-card system-health-card--unavailable">
        Health unavailable
      </div>
    )
  }

  const isHealthy = health.status === 'healthy'

  return (
    <div
      className={`system-health-card system-health-card--${health.status}`}
      aria-label="System health"
    >
      <div className="system-health-card__header">
        <span className="system-health-card__title">System</span>
        <span className={`system-health-card__badge system-health-card__badge--${health.status}`}>
          {isHealthy ? 'Healthy' : 'Degraded'}
        </span>
      </div>
      <dl className="system-health-card__grid">
        <div className="system-health-card__stat">
          <dt>Queued</dt>
          <dd>{health.queued_jobs}</dd>
        </div>
        <div className="system-health-card__stat">
          <dt>Running</dt>
          <dd>{health.running_jobs}</dd>
        </div>
        <div className={`system-health-card__stat${health.failed_jobs_1h > 0 ? ' system-health-card__stat--warn' : ''}`}>
          <dt>Failed (1h)</dt>
          <dd>{health.failed_jobs_1h}</dd>
        </div>
        {(!health.run_store_ok || !health.job_store_ok) && (
          <div className="system-health-card__stat system-health-card__stat--warn">
            <dt>Stores</dt>
            <dd>{[
              !health.run_store_ok && 'run',
              !health.job_store_ok && 'job',
            ].filter(Boolean).join(', ')} unavailable</dd>
          </div>
        )}
      </dl>
    </div>
  )
}
