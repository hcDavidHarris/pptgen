import { useState } from 'react'
import { fetchRunManifest } from '../api'

interface Props {
  runId: string
}

export function ManifestViewer({ runId }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [fetchTriggered, setFetchTriggered] = useState(false)
  const [data, setData] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  function handleToggle() {
    if (!expanded && !fetchTriggered) {
      // Lazy: only fetch on first expand
      setFetchTriggered(true)
      setLoading(true)
      fetchRunManifest(runId)
        .then((manifest) => {
          setData(manifest)
          setLoading(false)
        })
        .catch((err: unknown) => {
          setError(err instanceof Error ? err : new Error(String(err)))
          setLoading(false)
        })
    }
    setExpanded((v) => !v)
  }

  return (
    <section className="manifest-viewer">
      <button
        type="button"
        className="manifest-viewer__toggle"
        onClick={handleToggle}
        aria-expanded={expanded}
      >
        {expanded ? '▾' : '▸'} Manifest
      </button>

      {expanded && (
        <div className="manifest-viewer__content">
          {loading && <p aria-busy="true">Loading manifest…</p>}
          {error && (
            <p role="alert" className="manifest-viewer__error">
              Failed to load manifest: {error.message}
            </p>
          )}
          {!loading && !error && data !== null && (
            <pre className="manifest-viewer__json">
              {JSON.stringify(data, null, 2)}
            </pre>
          )}
        </div>
      )}
    </section>
  )
}
