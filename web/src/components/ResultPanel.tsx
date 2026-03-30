import { useState } from 'react'
import type { GenerateResponse } from '../types'
import { downloadUrl } from '../api'

interface Props {
  result: GenerateResponse
  /** 'preview' when preview_only was true; 'generate' otherwise. */
  mode: 'preview' | 'generate'
}

export function ResultPanel({ result, mode }: Props) {
  const isPreview = mode === 'preview'
  const heading = isPreview ? 'Preview' : 'Generated'

  const [idCopied, setIdCopied] = useState(false)

  function copyRequestId() {
    navigator.clipboard.writeText(result.request_id).then(() => {
      setIdCopied(true)
      setTimeout(() => setIdCopied(false), 2000)
    })
  }

  return (
    <section className="result-panel">
      <h2>{heading}</h2>

      <dl className="result-list">
        <dt>request_id</dt>
        <dd className="result-list__mono result-list__request-id">
          {result.request_id}
          <button
            type="button"
            className="btn btn--small btn--copy-id"
            onClick={copyRequestId}
            title="Copy request ID to clipboard"
            aria-label="Copy request ID"
          >
            {idCopied ? 'Copied!' : 'Copy'}
          </button>
        </dd>

        <dt>playbook</dt>
        <dd>
          {result.playbook_id}
          {result.content_intent_mode && (
            <span className="ci-badge" title="Deck built via content-intelligence path">
              {' '}CI
            </span>
          )}
        </dd>

        <dt>mode</dt>
        <dd>{result.mode}</dd>

        <dt>template</dt>
        <dd>{result.template_id ?? '(default)'}</dd>

        <dt>stage</dt>
        <dd>
          <span className={`stage-badge stage-badge--${result.stage}`}>
            {result.stage}
          </span>
        </dd>

        {result.slide_count != null && (
          <>
            <dt>slides</dt>
            <dd>{result.slide_count}</dd>
          </>
        )}

        {result.slide_types && result.slide_types.length > 0 && (
          <>
            <dt>slide types</dt>
            <dd>{result.slide_types.join(', ')}</dd>
          </>
        )}

        {result.notes && (
          <>
            <dt>notes</dt>
            <dd className="result-list__notes">{result.notes}</dd>
          </>
        )}

        {result.output_path && (
          <>
            <dt>output path</dt>
            <dd className="result-list__output-path">
              <code>{result.output_path}</code>
              <span className="output-actions">
                <button
                  type="button"
                  className="btn btn--small"
                  onClick={() => navigator.clipboard.writeText(result.output_path!)}
                  title="Copy path to clipboard"
                >
                  Copy path
                </button>
                <a
                  href={downloadUrl(result.output_path)}
                  download
                  className="btn btn--small btn--primary"
                >
                  Download .pptx
                </a>
              </span>
            </dd>
          </>
        )}

        {result.artifact_paths && (
          <>
            <dt>artifacts</dt>
            <dd>
              <ul className="artifact-list">
                {Object.entries(result.artifact_paths).map(([name, path]) => (
                  <li key={name}>
                    <span className="artifact-name">{name}</span>
                    <code className="artifact-path">{path}</code>
                  </li>
                ))}
              </ul>
            </dd>
          </>
        )}
      </dl>
    </section>
  )
}
