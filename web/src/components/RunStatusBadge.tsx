import type { RunStatus } from '../types'

interface Props {
  status: RunStatus
}

export function RunStatusBadge({ status }: Props) {
  return (
    <span className={`run-status-badge run-status-badge--${status}`}>
      {status}
    </span>
  )
}
