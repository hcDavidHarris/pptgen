import type { ArtifactMetadata } from '../types'
import { artifactDownloadUrl } from '../api'
import { formatBytes } from '../utils/format'

interface Props {
  artifacts: ArtifactMetadata[]
  loading: boolean
  error: Error | null
  onRetry?: () => void
}

type ArtifactCategory = 'final' | 'manifest' | 'internal'

function categorize(a: ArtifactMetadata): ArtifactCategory {
  if (a.is_final_output) return 'final'
  if (a.artifact_type === 'manifest') return 'manifest'
  return 'internal'
}

const CATEGORY_ORDER: Record<ArtifactCategory, number> = { final: 0, manifest: 1, internal: 2 }

const CATEGORY_ICON: Record<ArtifactCategory, string> = {
  final: '📊',
  manifest: '📋',
  internal: '📄',
}

function sortArtifacts(artifacts: ArtifactMetadata[]): ArtifactMetadata[] {
  return [...artifacts].sort((a, b) => {
    const catDiff = CATEGORY_ORDER[categorize(a)] - CATEGORY_ORDER[categorize(b)]
    if (catDiff !== 0) return catDiff
    // Secondary: backend timestamp DESC (most recent first)
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
}

export function ArtifactList({ artifacts, loading, error, onRetry }: Props) {
  if (loading) {
    return <p aria-busy="true">Loading artifacts…</p>
  }

  if (error) {
    return (
      <div className="artifact-list__error" role="alert">
        <p>Failed to load artifacts: {error.message}</p>
        {onRetry && (
          <button type="button" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    )
  }

  if (artifacts.length === 0) {
    return <p className="artifact-list__empty">No artifacts found. The run may still be in progress or artifacts were not retained.</p>
  }

  const sorted = sortArtifacts(artifacts)

  return (
    <ul className="artifact-list">
      {sorted.map((a) => {
        const category = categorize(a)
        const isPresent = a.status === 'present'
        return (
          <li
            key={a.artifact_id}
            className={`artifact-list__item artifact-list__item--${category}`}
            data-status={a.status}
          >
            <span className="artifact-list__icon" aria-hidden="true">{CATEGORY_ICON[category]}</span>
            <span className="artifact-list__filename">{a.filename}</span>
            <span className="artifact-list__type">{a.artifact_type}</span>
            <span className="artifact-list__size">{formatBytes(a.size_bytes)}</span>
            <span className="artifact-list__status">{a.status}</span>
            {isPresent && a.visibility === 'downloadable' && (
              <a
                href={artifactDownloadUrl(a.artifact_id)}
                className="artifact-list__download"
                download={a.filename}
              >
                Download
              </a>
            )}
          </li>
        )
      })}
    </ul>
  )
}
