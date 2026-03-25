import { useParams, NavLink } from 'react-router-dom'
import { useRunDetail } from '../hooks/useRunDetail'
import { useRunMetrics } from '../hooks/useRunMetrics'
import { useRunArtifacts } from '../hooks/useRunArtifacts'
import { RunSummaryCard } from '../components/RunSummaryCard'
import { RunMetricsCard } from '../components/RunMetricsCard'
import { ArtifactList } from '../components/ArtifactList'
import { ManifestViewer } from '../components/ManifestViewer'
import { ErrorState } from '../components/ErrorState'
import { artifactDownloadUrl } from '../api'
import type { ArtifactMetadata } from '../types'

function findFinalDeck(artifacts: ArtifactMetadata[]): ArtifactMetadata | null {
  const candidates = artifacts.filter(
    (a) => a.is_final_output && a.status === 'present'
  )
  if (candidates.length === 0) return null
  // Most recent by backend timestamp — never rely on array order
  return candidates.sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )[0]
}

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>()

  const { run, loading: runLoading, error: runError } = useRunDetail(runId ?? '')
  const { metrics, loading: metricsLoading } = useRunMetrics(runId ?? '')
  const {
    artifacts,
    loading: artifactsLoading,
    error: artifactsError,
  } = useRunArtifacts(runId ?? '')

  if (runLoading) {
    return (
      <main className="app-main">
        <p aria-busy="true">Loading run…</p>
      </main>
    )
  }

  if (runError) {
    return (
      <main className="app-main">
        <NavLink to="/runs">← Back to Runs</NavLink>
        <ErrorState error={runError} />
      </main>
    )
  }

  if (!run) return null

  const finalDeck = findFinalDeck(artifacts)

  return (
    <main className="page-container">
      <NavLink to="/runs" className="run-detail__back">← Back to Runs</NavLink>

      <div className="run-detail__header">
        <h2>Run Detail</h2>
        {finalDeck && (
          <a
            href={artifactDownloadUrl(finalDeck.artifact_id)}
            className="run-detail__download-cta"
            download={finalDeck.filename}
          >
            Download Presentation
          </a>
        )}
      </div>

      <div className="run-detail-grid">
        <RunSummaryCard run={run} />
        {!metricsLoading && metrics && (
          <RunMetricsCard metrics={metrics} />
        )}
      </div>

      <section className="run-detail__artifacts">
        <h3>Artifacts</h3>
        <ArtifactList
          artifacts={artifacts}
          loading={artifactsLoading}
          error={artifactsError}
        />
      </section>

      {run.manifest_path && (
        <ManifestViewer runId={run.run_id} />
      )}
    </main>
  )
}
