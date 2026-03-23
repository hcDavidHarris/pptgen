import type { ExecutionMode } from '../types'

interface Props {
  text: string
  onTextChange: (v: string) => void
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
  text,
  onTextChange,
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
  const canSubmit = text.trim().length > 0 && !loading

  return (
    <section className="form-panel">
      <h2>Input</h2>

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
