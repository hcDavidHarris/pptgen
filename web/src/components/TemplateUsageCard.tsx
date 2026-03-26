import { useNavigate } from 'react-router-dom'
import type { TemplateRunItem } from '../types'
import { RunStatusBadge } from './RunStatusBadge'
import { formatTime } from '../utils/format'
import type { RunStatus } from '../types'

interface Props {
  runs: TemplateRunItem[]
  loading: boolean
  error: Error | null
}

export function TemplateUsageCard({ runs, loading, error }: Props) {
  const navigate = useNavigate()

  const latestRun = runs.length > 0 ? runs[0] : null

  return (
    <section className="template-usage-card" aria-label="Template usage summary">
      <h3>Usage (last 30 days)</h3>

      {loading && <p aria-busy="true">Loading usage…</p>}
      {error && <p className="template-usage-card__error">Failed to load usage data.</p>}

      {!loading && !error && (
        <>
          <dl className="template-usage-card__stats">
            <div className="template-usage-card__stat">
              <dt>Total runs</dt>
              <dd>{runs.length}</dd>
            </div>
            {latestRun && (
              <div className="template-usage-card__stat">
                <dt>Latest run</dt>
                <dd>
                  <button
                    type="button"
                    className="template-usage-card__run-link"
                    onClick={() => navigate(`/runs/${latestRun.run_id}`)}
                  >
                    {latestRun.run_id.slice(0, 12)}…
                  </button>
                  {' '}
                  <RunStatusBadge status={latestRun.status as RunStatus} />
                  {' '}
                  {formatTime(latestRun.started_at)}
                </dd>
              </div>
            )}
          </dl>

          {runs.length > 0 && (
            <table className="template-usage-card__table">
              <thead>
                <tr>
                  <th scope="col">Run ID</th>
                  <th scope="col">Version</th>
                  <th scope="col">Status</th>
                  <th scope="col">Started</th>
                </tr>
              </thead>
              <tbody>
                {runs.slice(0, 10).map((r) => (
                  <tr
                    key={r.run_id}
                    className="template-usage-card__row"
                    onClick={() => navigate(`/runs/${r.run_id}`)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        navigate(`/runs/${r.run_id}`)
                      }
                    }}
                  >
                    <td><code>{r.run_id.slice(0, 12)}…</code></td>
                    <td>{r.template_version ?? '—'}</td>
                    <td><RunStatusBadge status={r.status as RunStatus} /></td>
                    <td>{formatTime(r.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {runs.length === 0 && (
            <p className="template-usage-card__empty">No runs in the last 30 days.</p>
          )}
        </>
      )}
    </section>
  )
}
