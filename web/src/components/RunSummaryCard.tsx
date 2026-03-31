import type { RunDetail, RunStatus } from '../types'
import { RunStatusBadge } from './RunStatusBadge'
import { CopyButton } from './CopyButton'
import { formatDuration, formatTime } from '../utils/format'

interface Props {
  run: RunDetail
}

function computedDuration(run: RunDetail): string {
  if (run.total_ms != null && run.total_ms > 0) return formatDuration(run.total_ms)
  if (run.status === 'running') {
    const elapsed = Date.now() - new Date(run.started_at).getTime()
    return formatDuration(elapsed)
  }
  if (run.completed_at) {
    const elapsed = new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()
    if (elapsed > 0) return formatDuration(elapsed)
  }
  return '—'
}

export function RunSummaryCard({ run }: Props) {
  return (
    <section className="run-summary-card" aria-label="Run summary">
      <h3>Summary</h3>
      <dl className="run-summary-card__fields">
        <div className="run-summary-card__field">
          <dt>Run ID</dt>
          <dd>
            {run.run_id}
            <CopyButton value={run.run_id} label="Copy run ID" />
          </dd>
        </div>
        <div className="run-summary-card__field">
          <dt>Status</dt>
          <dd><RunStatusBadge status={run.status as RunStatus} /></dd>
        </div>
        <div className="run-summary-card__field">
          <dt>Mode</dt>
          <dd>{run.mode}</dd>
        </div>
        <div className="run-summary-card__field">
          <dt>Playbook</dt>
          <dd>{run.playbook_id ?? '—'}</dd>
        </div>
        <div className="run-summary-card__field">
          <dt>Template</dt>
          <dd>{run.template_id ?? '—'}</dd>
        </div>
        <div className="run-summary-card__field">
          <dt>Source</dt>
          <dd>{run.source}</dd>
        </div>
        <div className="run-summary-card__field">
          <dt>Started</dt>
          <dd>{formatTime(run.started_at)}</dd>
        </div>
        <div className="run-summary-card__field">
          <dt>Completed</dt>
          <dd>{formatTime(run.completed_at)}</dd>
        </div>
        <div className="run-summary-card__field">
          <dt>Duration</dt>
          <dd>{computedDuration(run)}</dd>
        </div>
        {run.error_category && (
          <div className="run-summary-card__field run-summary-card__field--error">
            <dt>Error</dt>
            <dd>[{run.error_category}] {run.error_message}</dd>
          </div>
        )}
      </dl>
    </section>
  )
}
