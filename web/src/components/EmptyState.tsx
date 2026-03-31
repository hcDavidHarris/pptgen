interface Props {
  message?: string
}

export function EmptyState({ message = 'No items found.' }: Props) {
  return (
    <div className="empty-state" role="status">
      <p>{message}</p>
    </div>
  )
}
