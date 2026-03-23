import { useEffect, useState } from 'react'
import type { ExecutionMode, GenerateResponse } from './types'
import { ApiError } from './types'
import { fetchTemplates, generate } from './api'
import { GenerateForm } from './components/GenerateForm'
import { ResultPanel } from './components/ResultPanel'
import { StatusBanner } from './components/StatusBanner'

type ResultMode = 'preview' | 'generate'

export function App() {
  // ── form state ──────────────────────────────────────────────────────────
  const [text, setText] = useState('')
  const [mode, setMode] = useState<ExecutionMode>('deterministic')
  const [templateId, setTemplateId] = useState('')
  const [artifacts, setArtifacts] = useState(false)

  // ── async state ──────────────────────────────────────────────────────────
  const [templates, setTemplates] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('Working…')
  const [error, setError] = useState<ApiError | Error | null>(null)

  // ── result state ─────────────────────────────────────────────────────────
  const [result, setResult] = useState<GenerateResponse | null>(null)
  const [resultMode, setResultMode] = useState<ResultMode>('preview')

  // ── load templates on mount ───────────────────────────────────────────────
  useEffect(() => {
    fetchTemplates()
      .then(setTemplates)
      .catch((err: unknown) => {
        // Template load failure is non-fatal — just show empty list.
        console.warn('Could not load templates:', err)
      })
  }, [])

  // ── handlers ─────────────────────────────────────────────────────────────
  async function handlePreview() {
    setError(null)
    setResult(null)
    setLoading(true)
    setLoadingMessage('Planning deck…')
    try {
      const res = await generate({
        text,
        mode,
        template_id: templateId || undefined,
        artifacts: false,   // artifacts only meaningful for full generation
        preview_only: true,
      })
      setResult(res)
      setResultMode('preview')
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    setError(null)
    setResult(null)
    setLoading(true)
    setLoadingMessage('Generating presentation…')
    try {
      const res = await generate({
        text,
        mode,
        template_id: templateId || undefined,
        artifacts,
        preview_only: false,
      })
      setResult(res)
      setResultMode('generate')
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setLoading(false)
    }
  }

  // ── render ────────────────────────────────────────────────────────────────
  return (
    <div className="app">
      <header className="app-header">
        <h1>pptgen</h1>
        <p className="app-header__subtitle">Presentation Generator</p>
      </header>

      <main className="app-main">
        <GenerateForm
          text={text}
          onTextChange={setText}
          mode={mode}
          onModeChange={setMode}
          templateId={templateId}
          onTemplateChange={setTemplateId}
          templates={templates}
          artifacts={artifacts}
          onArtifactsChange={setArtifacts}
          onPreview={handlePreview}
          onGenerate={handleGenerate}
          loading={loading}
        />

        <div className="result-area">
          <StatusBanner
            loading={loading}
            loadingMessage={loadingMessage}
            error={error}
          />
          {result && !loading && (
            <ResultPanel result={result} mode={resultMode} />
          )}
        </div>
      </main>
    </div>
  )
}
