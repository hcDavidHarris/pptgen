import type { ApiError } from '../types'

interface Props {
  loading: boolean
  loadingMessage?: string
  error: ApiError | Error | null
}

export function StatusBanner({ loading, loadingMessage = 'Working…', error }: Props) {
  if (loading) {
    return (
      <div className="banner banner--loading" role="status" aria-live="polite">
        <span className="spinner" aria-hidden="true" />
        {loadingMessage}
      </div>
    )
  }

  if (error) {
    const requestId = 'requestId' in error ? (error as ApiError).requestId : null
    return (
      <div className="banner banner--error" role="alert">
        <strong>Error:</strong> {error.message}
        {requestId && (
          <span className="banner__request-id"> (request_id: {requestId})</span>
        )}
      </div>
    )
  }

  return null
}
