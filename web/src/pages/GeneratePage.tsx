import { useEffect, useState } from 'react'
import type { ExecutionMode, GenerateResponse } from '../types'
import { ApiError } from '../types'
import { fetchTemplates, generate } from '../api'
import { GenerateForm } from '../components/GenerateForm'
import { ResultPanel } from '../components/ResultPanel'
import { StatusBanner } from '../components/StatusBanner'

type ResultMode = 'preview' | 'generate'
export type InputMode = 'text' | 'content-intelligence' | 'transcript'

export function GeneratePage() {
  // ── form state ──────────────────────────────────────────────────────────
  const [inputMode, setInputMode] = useState<InputMode>('text')
  const [text, setText] = useState('')
  const [mode, setMode] = useState<ExecutionMode>('deterministic')
  const [templateId, setTemplateId] = useState('')
  const [artifacts, setArtifacts] = useState(false)

  // ── CI state ─────────────────────────────────────────────────────────────
  const [ciTopic, setCiTopic] = useState('')
  const [ciGoal, setCiGoal] = useState('')
  const [ciAudience, setCiAudience] = useState('')

  // ── Transcript state ──────────────────────────────────────────────────────
  const [transcriptTitle, setTranscriptTitle] = useState('')
  const [transcriptText, setTranscriptText] = useState('')
  const [transcriptMeetingType, setTranscriptMeetingType] = useState('')
  const [transcriptAudience, setTranscriptAudience] = useState('')

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

  // ── helpers ───────────────────────────────────────────────────────────────
  function buildRequest(previewOnly: boolean, includeArtifacts: boolean) {
    const isCiMode = inputMode === 'content-intelligence'
    const isTranscriptMode = inputMode === 'transcript'

    const ciPayload =
      isCiMode && ciTopic.trim()
        ? {
            topic: ciTopic.trim(),
            goal: ciGoal.trim() || undefined,
            audience: ciAudience.trim() || undefined,
          }
        : undefined

    const transcriptPayload =
      isTranscriptMode && transcriptTitle.trim() && transcriptText.trim()
        ? {
            title: transcriptTitle.trim(),
            content: transcriptText.trim(),
            metadata: {
              meeting_type: transcriptMeetingType || undefined,
              audience: transcriptAudience.trim() || undefined,
            },
          }
        : undefined

    return {
      // In CI and transcript modes `text` has no pipeline meaning.
      // Sending an empty string prevents the raw-text path from activating.
      text: isCiMode || isTranscriptMode ? '' : text,
      mode,
      template_id: templateId || undefined,
      artifacts: includeArtifacts,
      preview_only: previewOnly,
      content_intent: ciPayload,
      transcript_payload: transcriptPayload,
    }
  }

  // ── handlers ─────────────────────────────────────────────────────────────
  async function handlePreview() {
    setError(null)
    setResult(null)
    setLoading(true)
    setLoadingMessage('Planning deck…')
    try {
      const res = await generate(buildRequest(true, false))
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
      const res = await generate(buildRequest(false, artifacts))
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
    <main className="app-main">
      <GenerateForm
        inputMode={inputMode}
        onInputModeChange={setInputMode}
        text={text}
        onTextChange={setText}
        ciTopic={ciTopic}
        onCiTopicChange={setCiTopic}
        ciGoal={ciGoal}
        onCiGoalChange={setCiGoal}
        ciAudience={ciAudience}
        onCiAudienceChange={setCiAudience}
        transcriptTitle={transcriptTitle}
        onTranscriptTitleChange={setTranscriptTitle}
        transcriptText={transcriptText}
        onTranscriptTextChange={setTranscriptText}
        transcriptMeetingType={transcriptMeetingType}
        onTranscriptMeetingTypeChange={setTranscriptMeetingType}
        transcriptAudience={transcriptAudience}
        onTranscriptAudienceChange={setTranscriptAudience}
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
  )
}
