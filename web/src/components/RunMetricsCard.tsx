import type { RunMetrics } from '../types'
import { formatDuration } from '../utils/format'

interface Props {
  metrics: RunMetrics
}

export function RunMetricsCard({ metrics }: Props) {
  return (
    <section className="run-metrics-card" aria-label="Stage timings">
      <h3>Stage Timings</h3>
      <p>
        Total: <strong>{formatDuration(metrics.total_ms)}</strong>
        {metrics.artifact_count != null && (
          <> · Artifacts: <strong>{metrics.artifact_count}</strong></>
        )}
      </p>

      {metrics.stage_timings.length === 0 ? (
        <p className="run-metrics-card__empty">No stage timings recorded.</p>
      ) : (
        <table className="run-metrics-card__table">
          <thead>
            <tr>
              <th scope="col">Stage</th>
              <th scope="col">Duration</th>
            </tr>
          </thead>
          <tbody>
            {metrics.stage_timings.map((t) => (
              <tr
                key={t.stage}
                className={
                  t.stage === metrics.slowest_stage
                    ? 'run-metrics-card__row run-metrics-card__row--slowest'
                    : 'run-metrics-card__row'
                }
              >
                <td>{t.stage}</td>
                <td>{formatDuration(t.duration_ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {metrics.slowest_stage && (
        <p className="run-metrics-card__annotation">
          Slowest: <strong>{metrics.slowest_stage}</strong>
          {metrics.fastest_stage && metrics.fastest_stage !== metrics.slowest_stage && (
            <> · Fastest: <strong>{metrics.fastest_stage}</strong></>
          )}
        </p>
      )}
    </section>
  )
}
