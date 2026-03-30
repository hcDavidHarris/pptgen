import type { ExecutionMode } from '../types'
import type { InputMode } from '../pages/GeneratePage'

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
  const canSubmit = (isCi ? ciTopic.trim().length > 0 : text.trim().length > 0) && !loading

  return (
    <section className="form-panel">
      <h2>Input</h2>

      {/* Input mode toggle */}
      <fieldset className="mode-fieldset">
        <legend className="field-label">Input mode</legend>
        {(['text', 'content-intelligence'] as InputMode[]).map((m) => (
          <label key={m} className="radio-label">
            <input
              type="radio"
              name="input-mode"
              value={m}
              checked={inputMode === m}
              onChange={() => onInputModeChange(m)}
              disabled={loading}
            />
            {m === 'text' ? 'Raw text' : 'Content intelligence'}
          </label>
        ))}
      </fieldset>

      {isCi ? (
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
