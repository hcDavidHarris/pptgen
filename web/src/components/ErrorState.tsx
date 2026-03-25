interface Props {
  error: Error
  onRetry?: () => void
}

export function ErrorState({ error, onRetry }: Props) {
  return (
    <div className="error-state" role="alert">
      <p>{error.message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}
