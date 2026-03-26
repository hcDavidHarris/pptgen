import { useState } from 'react'
import { cancelJob } from '../api'
import type { RunDetail } from '../types'

interface Props {
  run: RunDetail
  onCancelled?: () => void
}

export function CancelJobButton({ run, onCancelled }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Only show if there's a linked job and the run is still running
  if (!run.job_id || run.status !== 'running') return null

  async function handleClick() {
    if (!run.job_id) return
    setLoading(true)
    setError(null)
    try {
      await cancelJob(run.job_id)
      onCancelled?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="run-action">
      <button
        type="button"
        className="btn btn--danger btn--small"
        onClick={handleClick}
        disabled={loading}
        aria-label="Cancel this job"
      >
        {loading ? 'Cancelling…' : 'Cancel'}
      </button>
      {error && <span className="run-action__error" role="alert">{error}</span>}
    </div>
  )
}
