import type { JobStatus } from '../types'

interface Props {
  status: JobStatus
}

export function JobStatusBadge({ status }: Props) {
  return (
    <span className={`job-status-badge job-status-badge--${status}`}>
      {status}
    </span>
  )
}
