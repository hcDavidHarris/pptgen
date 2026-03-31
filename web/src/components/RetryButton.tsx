import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { retryRun } from '../api'
import type { RunDetail } from '../types'

interface Props {
  run: RunDetail
}

export function RetryButton({ run }: Props) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (run.status !== 'failed' || !run.replay_available) return null

  async function handleClick() {
    setLoading(true)
    setError(null)
    try {
      const result = await retryRun(run.run_id)
      navigate(`/runs/${result.run_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Retry failed')
      setLoading(false)
    }
  }

  return (
    <div className="run-action">
      <button
        type="button"
        className="btn btn--primary btn--small"
        onClick={handleClick}
        disabled={loading}
        aria-label="Retry this run"
      >
        {loading ? 'Retrying…' : 'Retry'}
      </button>
      {error && <span className="run-action__error" role="alert">{error}</span>}
    </div>
  )
}
