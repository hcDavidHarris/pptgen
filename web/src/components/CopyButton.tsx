import { useState } from 'react'

interface Props {
  value: string
  label?: string
}

export function CopyButton({ value, label = 'Copy' }: Props) {
  const [copied, setCopied] = useState(false)

  async function handleClick() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard API unavailable — silent fail
    }
  }

  return (
    <button
      type="button"
      className="btn btn--secondary btn--small btn--copy-id"
      onClick={handleClick}
      aria-label={copied ? 'Copied!' : label}
      title={copied ? 'Copied!' : label}
    >
      {copied ? '✓' : '⎘'}
    </button>
  )
}
