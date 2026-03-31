import type { RunDetail, RunMetrics, StageTimer } from '../types'

const HINTS: Record<string, string> = {
  TemplateError: 'Verify the template exists and is registered in registry.yaml.',
  ArtifactError: 'Check artifact promotion and storage configuration.',
  ValidationError: 'Review required input structure and schema expectations.',
  TimeoutError: 'The pipeline exceeded its timeout. Consider reducing input size.',
  RoutingError: 'No matching playbook was found for this input type.',
  PipelineError: 'An unexpected pipeline error occurred. Review logs for details.',
}

function lastRecordedStage(timings: StageTimer[]): string | null {
  if (timings.length === 0) return null
  return timings[timings.length - 1].stage
}

interface Props {
  run: RunDetail
  metrics: RunMetrics | null
}

export function RunDiagnosticsCard({ run, metrics }: Props) {
  if (run.status !== 'failed') return null

  const hint = run.error_category ? (HINTS[run.error_category] ?? null) : null
  const lastStage = metrics ? lastRecordedStage(metrics.stage_timings) : null

  const artifactCount = run.artifact_count ?? metrics?.artifact_count ?? 0
  const hasArtifacts = (artifactCount > 0)

  return (
    <section className="run-diagnostics-card" aria-label="Run diagnostics" role="region">
      <h3>Diagnostics</h3>
      <dl className="run-diagnostics-card__fields">
        <div className="run-diagnostics-card__field">
          <dt>Error category</dt>
          <dd>{run.error_category ?? '—'}</dd>
        </div>
        <div className="run-diagnostics-card__field">
          <dt>Error message</dt>
          <dd className="run-diagnostics-card__message">
            {run.error_message ?? '—'}
          </dd>
        </div>
        <div className="run-diagnostics-card__field">
          <dt>Last recorded stage</dt>
          <dd>{lastStage ?? '—'}</dd>
        </div>
        {run.retry_count != null && (
          <div className="run-diagnostics-card__field">
            <dt>Retry count</dt>
            <dd>{run.retry_count}</dd>
          </div>
        )}
        <div className="run-diagnostics-card__field">
          <dt>Artifacts available</dt>
          <dd>{hasArtifacts ? 'Yes' : 'None'}</dd>
        </div>
      </dl>

      {hint && (
        <div className="run-diagnostics-card__hint" role="note">
          <span className="run-diagnostics-card__hint-icon" aria-hidden="true">ℹ</span>
          {hint}
        </div>
      )}
    </section>
  )
}
