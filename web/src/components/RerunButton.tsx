import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { rerunRun } from '../api'
import type { RunDetail } from '../types'

interface Props {
  run: RunDetail
}

export function RerunButton({ run }: Props) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!run.replay_available) return null

  async function handleClick() {
    setLoading(true)
    setError(null)
    try {
      const result = await rerunRun(run.run_id)
      navigate(`/runs/${result.run_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rerun failed')
      setLoading(false)
    }
  }

  return (
    <div className="run-action">
      <button
        type="button"
        className="btn btn--secondary btn--small"
        onClick={handleClick}
        disabled={loading}
        aria-label="Rerun this run"
      >
        {loading ? 'Rerunning…' : 'Rerun'}
      </button>
      {error && <span className="run-action__error" role="alert">{error}</span>}
    </div>
  )
}
