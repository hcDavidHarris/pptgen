import { useNavigate } from 'react-router-dom'
import type { RunListItem, RunStatus } from '../types'
import { RunStatusBadge } from './RunStatusBadge'
import { formatDuration, formatTime } from '../utils/format'

interface Props {
  runs: RunListItem[]
  selectedIds?: Set<string>
  onToggleSelect?: (id: string) => void
}

function computedDuration(run: RunListItem): string {
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

export function RunTable({ runs, selectedIds, onToggleSelect }: Props) {
  const navigate = useNavigate()
  const selectable = selectedIds !== undefined && onToggleSelect !== undefined

  function handleRowClick(runId: string) {
    navigate(`/runs/${runId}`)
  }

  function handleRowKeyDown(e: React.KeyboardEvent, runId: string) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      navigate(`/runs/${runId}`)
    }
  }

  return (
    <table className="run-table">
      <thead>
        <tr>
          {selectable && <th scope="col" className="run-table__select-col" aria-label="Select" />}
          <th scope="col">Run ID</th>
          <th scope="col">Status</th>
          <th scope="col">Playbook</th>
          <th scope="col">Mode</th>
          <th scope="col">Started</th>
          <th scope="col">Duration</th>
          <th scope="col">Artifacts</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr
            key={run.run_id}
            className={`run-table__row${run.status === 'failed' ? ' run-table__row--failed' : ''}`}
            onClick={() => handleRowClick(run.run_id)}
            onKeyDown={(e) => handleRowKeyDown(e, run.run_id)}
            tabIndex={0}
            role="link"
            aria-label={`Run ${run.run_id}`}
          >
            {selectable && (
              <td className="run-table__select-cell">
                <input
                  type="checkbox"
                  aria-label={`Select run ${run.run_id}`}
                  checked={selectedIds.has(run.run_id)}
                  onClick={(e) => e.stopPropagation()}
                  onChange={() => onToggleSelect(run.run_id)}
                />
              </td>
            )}
            <td className="run-table__run-id" title={run.run_id}>{run.run_id.substring(0, 8)}…</td>
            <td><RunStatusBadge status={run.status as RunStatus} /></td>
            <td>{run.playbook_id ?? '—'}</td>
            <td>{run.mode}</td>
            <td>{formatTime(run.started_at)}</td>
            <td>{computedDuration(run)}</td>
            <td>{run.artifact_count ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
