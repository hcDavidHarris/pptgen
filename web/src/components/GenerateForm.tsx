import type { ExecutionMode } from '../types'
import type { InputMode } from '../pages/GeneratePage'

const MEETING_TYPE_OPTIONS = [
  { value: '', label: '(auto-detect)' },
  { value: 'standard', label: 'Standard' },
  { value: 'eos', label: 'EOS' },
  { value: 'l10', label: 'L10' },
  { value: 'rocks', label: 'Rocks review' },
] as const

interface Props {
  inputMode: InputMode
  onInputModeChange: (v: InputMode) => void
  text: string
  onTextChange: (v: string) => void
  ciTopic: string
  onCiTopicChange: (v: string) => void
  ciGoal: string
  onCiGoalChange: (v: string) => void
  ciAudience: string
  onCiAudienceChange: (v: string) => void
  transcriptTitle: string
  onTranscriptTitleChange: (v: string) => void
  transcriptText: string
  onTranscriptTextChange: (v: string) => void
  transcriptMeetingType: string
  onTranscriptMeetingTypeChange: (v: string) => void
  transcriptAudience: string
  onTranscriptAudienceChange: (v: string) => void
  adoBoardTitle: string
  onAdoBoardTitleChange: (v: string) => void
  adoBoardWorkItemsJson: string
  onAdoBoardWorkItemsJsonChange: (v: string) => void
  adoBoardIteration: string
  onAdoBoardIterationChange: (v: string) => void
  adoBoardTeam: string
  onAdoBoardTeamChange: (v: string) => void
  mode: ExecutionMode
  onModeChange: (v: ExecutionMode) => void
  templateId: string
  onTemplateChange: (v: string) => void
  templates: string[]
  artifacts: boolean
  onArtifactsChange: (v: boolean) => void
  onPreview: () => void
  onGenerate: () => void
  loading: boolean
}

export function GenerateForm({
  inputMode,
  onInputModeChange,
  text,
  onTextChange,
  ciTopic,
  onCiTopicChange,
  ciGoal,
  onCiGoalChange,
  ciAudience,
  onCiAudienceChange,
  transcriptTitle,
  onTranscriptTitleChange,
  transcriptText,
  onTranscriptTextChange,
  transcriptMeetingType,
  onTranscriptMeetingTypeChange,
  transcriptAudience,
  onTranscriptAudienceChange,
  adoBoardTitle,
  onAdoBoardTitleChange,
  adoBoardWorkItemsJson,
  onAdoBoardWorkItemsJsonChange,
  adoBoardIteration,
  onAdoBoardIterationChange,
  adoBoardTeam,
  onAdoBoardTeamChange,
  mode,
  onModeChange,
  templateId,
  onTemplateChange,
  templates,
  artifacts,
  onArtifactsChange,
  onPreview,
  onGenerate,
  loading,
}: Props) {
  const isCi = inputMode === 'content-intelligence'
  const isTranscript = inputMode === 'transcript'
  const isAdoBoard = inputMode === 'ado-board'

  // Validate work items JSON inline — computed, no state needed.
  // Only active when ADO board mode is selected and the textarea is non-empty.
  const adoBoardJsonError: string | null = (() => {
    if (!isAdoBoard || !adoBoardWorkItemsJson.trim()) return null
    try {
      const parsed = JSON.parse(adoBoardWorkItemsJson.trim())
      if (!Array.isArray(parsed)) {
        return 'Work items must be a JSON array — e.g. [ { "title": "…", "state": "Active" }, … ]'
      }
      return null
    } catch {
      return 'Invalid JSON — check for missing quotes, commas, or brackets.'
    }
  })()

  const canSubmit = (
    isAdoBoard
      ? adoBoardTitle.trim().length > 0 && adoBoardJsonError === null
      : isTranscript
        ? transcriptTitle.trim().length > 0 && transcriptText.trim().length > 0
        : isCi
          ? ciTopic.trim().length > 0
          : text.trim().length > 0
  ) && !loading

  return (
    <section className="form-panel">
      <h2>Input</h2>

      {/* Input mode toggle */}
      <fieldset className="mode-fieldset">
        <legend className="field-label">Input mode</legend>
        {(['text', 'content-intelligence', 'transcript', 'ado-board'] as InputMode[]).map((m) => (
          <label key={m} className="radio-label">
            <input
              type="radio"
              name="input-mode"
              value={m}
              checked={inputMode === m}
              onChange={() => onInputModeChange(m)}
              disabled={loading}
            />
            {m === 'text'
              ? 'Raw text'
              : m === 'content-intelligence'
                ? 'Content intelligence'
                : m === 'transcript'
                  ? 'Transcript'
                  : 'ADO Boards'}
          </label>
        ))}
      </fieldset>

      {isAdoBoard ? (
        <>
          <label htmlFor="ado-board-title" className="field-label">
            Board title <span aria-hidden="true">*</span>
          </label>
          <input
            id="ado-board-title"
            type="text"
            className="input-text"
            value={adoBoardTitle}
            onChange={(e) => onAdoBoardTitleChange(e.target.value)}
            placeholder="e.g. Q3 Delivery Status"
            disabled={loading}
          />

          <label htmlFor="ado-board-work-items" className="field-label">
            Work items JSON (optional)
          </label>
          <textarea
            id="ado-board-work-items"
            className={`input-textarea${adoBoardJsonError ? ' input-textarea--error' : ''}`}
            value={adoBoardWorkItemsJson}
            onChange={(e) => onAdoBoardWorkItemsJsonChange(e.target.value)}
            placeholder={'Paste a JSON array of work items, e.g.\n[\n  {"id": 101, "title": "...", "state": "In Progress", "type": "Feature", "priority": 1}\n]'}
            rows={10}
            disabled={loading}
            aria-describedby={adoBoardJsonError ? 'ado-board-work-items-error' : undefined}
          />
          {adoBoardJsonError && (
            <p id="ado-board-work-items-error" className="field-error" role="alert">
              {adoBoardJsonError}
            </p>
          )}

          <div className="field-row">
            <div className="template-field">
              <label htmlFor="ado-board-iteration" className="field-label">
                Iteration / sprint (optional)
              </label>
              <input
                id="ado-board-iteration"
                type="text"
                className="input-text"
                value={adoBoardIteration}
                onChange={(e) => onAdoBoardIterationChange(e.target.value)}
                placeholder="e.g. Sprint 42"
                disabled={loading}
              />
            </div>

            <div className="template-field">
              <label htmlFor="ado-board-team" className="field-label">
                Team (optional)
              </label>
              <input
                id="ado-board-team"
                type="text"
                className="input-text"
                value={adoBoardTeam}
                onChange={(e) => onAdoBoardTeamChange(e.target.value)}
                placeholder="e.g. Interchange"
                disabled={loading}
              />
            </div>
          </div>
        </>
      ) : isTranscript ? (
        <>
          <label htmlFor="transcript-title" className="field-label">
            Meeting title <span aria-hidden="true">*</span>
          </label>
          <input
            id="transcript-title"
            type="text"
            className="input-text"
            value={transcriptTitle}
            onChange={(e) => onTranscriptTitleChange(e.target.value)}
            placeholder="e.g. Q3 Leadership Sync"
            disabled={loading}
          />

          <label htmlFor="transcript-text" className="field-label">
            Transcript <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="transcript-text"
            className="input-textarea"
            value={transcriptText}
            onChange={(e) => onTranscriptTextChange(e.target.value)}
            placeholder="Paste the meeting transcript here…"
            rows={12}
            disabled={loading}
          />

          <div className="field-row">
            <div className="template-field">
              <label htmlFor="transcript-meeting-type" className="field-label">
                Meeting type (optional)
              </label>
              <select
                id="transcript-meeting-type"
                value={transcriptMeetingType}
                onChange={(e) => onTranscriptMeetingTypeChange(e.target.value)}
                disabled={loading}
              >
                {MEETING_TYPE_OPTIONS.map(({ value, label }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            <div className="template-field">
              <label htmlFor="transcript-audience" className="field-label">
                Audience (optional)
              </label>
              <input
                id="transcript-audience"
                type="text"
                className="input-text"
                value={transcriptAudience}
                onChange={(e) => onTranscriptAudienceChange(e.target.value)}
                placeholder="e.g. Leadership team"
                disabled={loading}
              />
            </div>
          </div>
        </>
      ) : isCi ? (
        <>
          <label htmlFor="ci-topic" className="field-label">
            Topic <span aria-hidden="true">*</span>
          </label>
          <input
            id="ci-topic"
            type="text"
            className="input-text"
            value={ciTopic}
            onChange={(e) => onCiTopicChange(e.target.value)}
            placeholder="e.g. Cloud Cost Optimisation"
            disabled={loading}
          />

          <label htmlFor="ci-goal" className="field-label">
            Goal (optional)
          </label>
          <input
            id="ci-goal"
            type="text"
            className="input-text"
            value={ciGoal}
            onChange={(e) => onCiGoalChange(e.target.value)}
            placeholder="e.g. Secure leadership commitment to a 3-year platform investment"
            disabled={loading}
          />

          <label htmlFor="ci-audience" className="field-label">
            Audience (optional)
          </label>
          <input
            id="ci-audience"
            type="text"
            className="input-text"
            value={ciAudience}
            onChange={(e) => onCiAudienceChange(e.target.value)}
            placeholder="e.g. Engineering leadership"
            disabled={loading}
          />
        </>
      ) : (
        <>
          <label htmlFor="input-text" className="field-label">
            Raw input text
          </label>
          <textarea
            id="input-text"
            className="input-textarea"
            value={text}
            onChange={(e) => onTextChange(e.target.value)}
            placeholder="Paste meeting notes, sprint data, ADO export, etc."
            rows={10}
            disabled={loading}
          />
        </>
      )}

      <div className="field-row">
        <fieldset className="mode-fieldset">
          <legend className="field-label">Execution mode</legend>
          {(['deterministic', 'ai'] as ExecutionMode[]).map((m) => (
            <label key={m} className="radio-label">
              <input
                type="radio"
                name="mode"
                value={m}
                checked={mode === m}
                onChange={() => onModeChange(m)}
                disabled={loading}
              />
              {m}
            </label>
          ))}
        </fieldset>

        <div className="template-field">
          <label htmlFor="template-select" className="field-label">
            Template
          </label>
          <select
            id="template-select"
            value={templateId}
            onChange={(e) => onTemplateChange(e.target.value)}
            disabled={loading}
          >
            <option value="">(auto-select)</option>
            {templates.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={artifacts}
          onChange={(e) => onArtifactsChange(e.target.checked)}
          disabled={loading}
        />
        Export pipeline artifacts (spec.json, slide_plan.json, deck_definition.json)
      </label>

      <div className="button-row">
        <button
          type="button"
          className="btn btn--secondary"
          onClick={onPreview}
          disabled={!canSubmit}
          title="Plan the deck without rendering a .pptx"
        >
          Preview
        </button>
        <button
          type="button"
          className="btn btn--primary"
          onClick={onGenerate}
          disabled={!canSubmit}
        >
          Generate
        </button>
      </div>
    </section>
  )
}
