import { useNavigate } from 'react-router-dom'
import { JobStatusBadge } from './JobStatusBadge'
import { cancelJob } from '../api'
import { formatTime } from '../utils/format'
import type { JobListItem, JobStatus } from '../types'

const CANCELLABLE: Set<JobStatus> = new Set(['queued', 'retrying', 'running'])

interface Props {
  jobs: JobListItem[]
  onRefresh?: () => void
}

export function JobsTable({ jobs, onRefresh }: Props) {
  const navigate = useNavigate()

  async function handleCancel(e: React.MouseEvent, jobId: string) {
    e.stopPropagation()
    await cancelJob(jobId)
    onRefresh?.()
  }

  return (
    <table className="jobs-table">
      <thead>
        <tr>
          <th scope="col">Job ID</th>
          <th scope="col">Status</th>
          <th scope="col">Run ID</th>
          <th scope="col">Submitted</th>
          <th scope="col">Retries</th>
          <th scope="col">Actions</th>
        </tr>
      </thead>
      <tbody>
        {jobs.map((job) => (
          <tr
            key={job.job_id}
            className="jobs-table__row"
            onClick={() => navigate(`/runs/${job.run_id}`)}
            role="link"
            tabIndex={0}
            aria-label={`Job ${job.job_id}`}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                navigate(`/runs/${job.run_id}`)
              }
            }}
          >
            <td className="jobs-table__job-id" title={job.job_id}>{job.job_id.substring(0, 8)}…</td>
            <td><JobStatusBadge status={job.status} /></td>
            <td className="jobs-table__run-id" title={job.run_id}>{job.run_id.substring(0, 8)}…</td>
            <td>{formatTime(job.submitted_at)}</td>
            <td>{job.retry_count}</td>
            <td onClick={(e) => e.stopPropagation()}>
              {CANCELLABLE.has(job.status) && (
                <button
                  type="button"
                  className="btn btn--danger btn--small"
                  onClick={(e) => handleCancel(e, job.job_id)}
                  aria-label={`Cancel job ${job.job_id}`}
                >
                  Cancel
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
