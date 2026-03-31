import type { TemplateUsageSummary, TemplateVersionUsageItem, TemplateUsageTrendItem } from '../types'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(rate: number | null): string {
  if (rate == null) return '—'
  return `${(rate * 100).toFixed(1)}%`
}

function shortDate(iso: string | null): string {
  if (!iso) return '—'
  return iso.slice(0, 10)
}

// ---------------------------------------------------------------------------
// Summary card
// ---------------------------------------------------------------------------

interface SummaryCardProps {
  summary: TemplateUsageSummary
}

function UsageSummaryCard({ summary }: SummaryCardProps) {
  return (
    <div className="analytics-summary-card">
      <dl className="analytics-summary-card__fields">
        <div className="analytics-summary-card__field">
          <dt>Total Runs</dt>
          <dd>{summary.total_runs}</dd>
        </div>
        <div className="analytics-summary-card__field">
          <dt>Completed</dt>
          <dd>{summary.completed_runs}</dd>
        </div>
        <div className="analytics-summary-card__field">
          <dt>Failed</dt>
          <dd>{summary.failed_runs}</dd>
        </div>
        <div className="analytics-summary-card__field">
          <dt>Cancelled</dt>
          <dd>{summary.cancelled_runs}</dd>
        </div>
        <div className="analytics-summary-card__field">
          <dt>Failure Rate</dt>
          <dd className={summary.failure_rate != null && summary.failure_rate > 0.1 ? 'analytics-summary-card__value--high-failure' : ''}>
            {pct(summary.failure_rate)}
          </dd>
        </div>
        <div className="analytics-summary-card__field">
          <dt>Window</dt>
          <dd>Last {summary.date_window_days} days</dd>
        </div>
      </dl>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Version usage table
// ---------------------------------------------------------------------------

interface VersionTableProps {
  versions: TemplateVersionUsageItem[]
}

function VersionUsageTable({ versions }: VersionTableProps) {
  if (versions.length === 0) {
    return <p className="analytics-empty">No version data in this window.</p>
  }

  return (
    <table className="analytics-version-table">
      <thead>
        <tr>
          <th scope="col">Version</th>
          <th scope="col">Runs</th>
          <th scope="col">Failed</th>
          <th scope="col">Failure Rate</th>
          <th scope="col">First Seen</th>
          <th scope="col">Last Seen</th>
        </tr>
      </thead>
      <tbody>
        {versions.map((v) => (
          <tr key={v.template_version} className="analytics-version-table__row">
            <td><code>{v.template_version}</code></td>
            <td>{v.total_runs}</td>
            <td>{v.failed_runs}</td>
            <td>{pct(v.failure_rate)}</td>
            <td>{shortDate(v.first_seen_at)}</td>
            <td>{shortDate(v.last_seen_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ---------------------------------------------------------------------------
// Trend table
// ---------------------------------------------------------------------------

interface TrendTableProps {
  trend: TemplateUsageTrendItem[]
}

function UsageTrendTable({ trend }: TrendTableProps) {
  if (trend.length === 0) {
    return <p className="analytics-empty">No trend data in this window.</p>
  }

  return (
    <table className="analytics-trend-table">
      <thead>
        <tr>
          <th scope="col">Date</th>
          <th scope="col">Version</th>
          <th scope="col">Runs</th>
        </tr>
      </thead>
      <tbody>
        {trend.map((t, i) => (
          <tr key={`${t.date}-${t.template_version}-${i}`} className="analytics-trend-table__row">
            <td>{t.date}</td>
            <td><code>{t.template_version}</code></td>
            <td>{t.run_count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ---------------------------------------------------------------------------
// Root section
// ---------------------------------------------------------------------------

interface TemplateAnalyticsSectionProps {
  summary: TemplateUsageSummary | null
  versions: TemplateVersionUsageItem[]
  trend: TemplateUsageTrendItem[]
  loading: boolean
  error: Error | null
}

export function TemplateAnalyticsSection({
  summary,
  versions,
  trend,
  loading,
  error,
}: TemplateAnalyticsSectionProps) {
  return (
    <section className="template-analytics card" aria-label="Usage Analytics">
      <h3>Usage Analytics</h3>

      {loading && <p aria-busy="true">Loading analytics…</p>}

      {error && (
        <p className="template-analytics__error" role="alert">
          Analytics unavailable: {error.message}
        </p>
      )}

      {!loading && !error && summary && (
        <>
          <h4>Summary (last {summary.date_window_days} days)</h4>
          <UsageSummaryCard summary={summary} />

          <h4>Per-Version Usage</h4>
          <VersionUsageTable versions={versions} />

          <h4>Daily Adoption Trend</h4>
          <UsageTrendTable trend={trend} />
        </>
      )}

      {!loading && !error && !summary && (
        <p className="analytics-empty">No analytics data available.</p>
      )}
    </section>
  )
}
