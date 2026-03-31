import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GenerateForm } from '../components/GenerateForm'

const defaultProps = {
  text: '',
  onTextChange: vi.fn(),
  mode: 'deterministic' as const,
  onModeChange: vi.fn(),
  templateId: '',
  onTemplateChange: vi.fn(),
  templates: ['ops_review_v1', 'executive_brief_v1'],
  artifacts: false,
  onArtifactsChange: vi.fn(),
  onPreview: vi.fn(),
  onGenerate: vi.fn(),
  loading: false,
  // CI mode props (default to empty for text-mode tests)
  ciTopic: '',
  onCiTopicChange: vi.fn(),
  ciGoal: '',
  onCiGoalChange: vi.fn(),
  ciAudience: '',
  onCiAudienceChange: vi.fn(),
  // Transcript mode props (default to empty for text-mode tests)
  transcriptTitle: '',
  onTranscriptTitleChange: vi.fn(),
  transcriptText: '',
  onTranscriptTextChange: vi.fn(),
  transcriptMeetingType: '',
  onTranscriptMeetingTypeChange: vi.fn(),
  transcriptAudience: '',
  onTranscriptAudienceChange: vi.fn(),
  // input mode (default to text for most tests)
  inputMode: 'text' as const,
  onInputModeChange: vi.fn(),
}

describe('GenerateForm', () => {
  it('renders the textarea in text mode', () => {
    render(<GenerateForm {...defaultProps} />)
    expect(screen.getByRole('textbox', { name: /raw input text/i })).toBeInTheDocument()
  })

  it('renders both mode radio buttons', () => {
    render(<GenerateForm {...defaultProps} />)
    expect(screen.getByRole('radio', { name: 'deterministic' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'ai' })).not.toBeChecked()
  })

  it('renders template options from props', () => {
    render(<GenerateForm {...defaultProps} />)
    expect(screen.getByRole('option', { name: 'ops_review_v1' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'executive_brief_v1' })).toBeInTheDocument()
  })

  it('renders (auto-select) as default option', () => {
    render(<GenerateForm {...defaultProps} />)
    expect(screen.getByRole('option', { name: '(auto-select)' })).toBeInTheDocument()
  })

  it('renders Preview and Generate buttons', () => {
    render(<GenerateForm {...defaultProps} />)
    expect(screen.getByRole('button', { name: 'Preview' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate' })).toBeInTheDocument()
  })

  it('disables buttons when text is empty', () => {
    render(<GenerateForm {...defaultProps} text="" />)
    expect(screen.getByRole('button', { name: 'Preview' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Generate' })).toBeDisabled()
  })

  it('enables buttons when text is non-empty', () => {
    render(<GenerateForm {...defaultProps} text="Meeting notes here." />)
    expect(screen.getByRole('button', { name: 'Preview' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Generate' })).toBeEnabled()
  })

  it('disables everything when loading', () => {
    render(<GenerateForm {...defaultProps} text="some text" loading={true} />)
    expect(screen.getByRole('button', { name: 'Preview' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Generate' })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: /raw input text/i })).toBeDisabled()
  })

  it('calls onPreview when Preview clicked', async () => {
    const onPreview = vi.fn()
    const user = userEvent.setup()
    render(<GenerateForm {...defaultProps} text="some text" onPreview={onPreview} />)
    await user.click(screen.getByRole('button', { name: 'Preview' }))
    expect(onPreview).toHaveBeenCalledOnce()
  })

  it('calls onGenerate when Generate clicked', async () => {
    const onGenerate = vi.fn()
    const user = userEvent.setup()
    render(<GenerateForm {...defaultProps} text="some text" onGenerate={onGenerate} />)
    await user.click(screen.getByRole('button', { name: 'Generate' }))
    expect(onGenerate).toHaveBeenCalledOnce()
  })

  it('calls onTextChange when typing', async () => {
    const onTextChange = vi.fn()
    const user = userEvent.setup()
    render(<GenerateForm {...defaultProps} onTextChange={onTextChange} />)
    await user.type(screen.getByRole('textbox', { name: /raw input text/i }), 'hi')
    expect(onTextChange).toHaveBeenCalled()
  })

  it('calls onModeChange when ai radio clicked', async () => {
    const onModeChange = vi.fn()
    const user = userEvent.setup()
    render(<GenerateForm {...defaultProps} onModeChange={onModeChange} />)
    await user.click(screen.getByRole('radio', { name: 'ai' }))
    expect(onModeChange).toHaveBeenCalledWith('ai')
  })

  it('renders artifacts checkbox unchecked by default', () => {
    render(<GenerateForm {...defaultProps} />)
    expect(screen.getByRole('checkbox', { name: /export pipeline artifacts/i })).not.toBeChecked()
  })

  it('calls onArtifactsChange when checkbox toggled', async () => {
    const onArtifactsChange = vi.fn()
    const user = userEvent.setup()
    render(<GenerateForm {...defaultProps} onArtifactsChange={onArtifactsChange} />)
    await user.click(screen.getByRole('checkbox', { name: /export pipeline artifacts/i }))
    expect(onArtifactsChange).toHaveBeenCalledWith(true)
  })

  it('renders Transcript radio option', () => {
    render(<GenerateForm {...defaultProps} />)
    expect(screen.getByRole('radio', { name: 'Transcript' })).toBeInTheDocument()
  })

  it('calls onInputModeChange with "transcript" when Transcript radio clicked', async () => {
    const onInputModeChange = vi.fn()
    const user = userEvent.setup()
    render(<GenerateForm {...defaultProps} onInputModeChange={onInputModeChange} />)
    await user.click(screen.getByRole('radio', { name: 'Transcript' }))
    expect(onInputModeChange).toHaveBeenCalledWith('transcript')
  })
})

// ---------------------------------------------------------------------------
// Transcript mode
// ---------------------------------------------------------------------------

describe('GenerateForm — transcript mode', () => {
  const transcriptProps = {
    ...defaultProps,
    inputMode: 'transcript' as const,
  }

  it('shows Meeting title field in transcript mode', () => {
    render(<GenerateForm {...transcriptProps} />)
    expect(screen.getByRole('textbox', { name: /meeting title/i })).toBeInTheDocument()
  })

  it('shows Transcript textarea in transcript mode', () => {
    render(<GenerateForm {...transcriptProps} />)
    expect(screen.getByRole('textbox', { name: /^Transcript/i })).toBeInTheDocument()
  })

  it('hides raw input textarea in transcript mode', () => {
    render(<GenerateForm {...transcriptProps} />)
    expect(screen.queryByRole('textbox', { name: /raw input text/i })).not.toBeInTheDocument()
  })

  it('shows Meeting type dropdown in transcript mode', () => {
    render(<GenerateForm {...transcriptProps} />)
    expect(screen.getByRole('combobox', { name: /meeting type/i })).toBeInTheDocument()
  })

  it('meeting type dropdown has standard and EOS options', () => {
    render(<GenerateForm {...transcriptProps} />)
    expect(screen.getByRole('option', { name: 'Standard' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'EOS' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'L10' })).toBeInTheDocument()
  })

  it('shows Audience field in transcript mode', () => {
    render(<GenerateForm {...transcriptProps} />)
    expect(screen.getByRole('textbox', { name: /audience/i })).toBeInTheDocument()
  })

  it('disables Generate when title is empty in transcript mode', () => {
    render(<GenerateForm {...transcriptProps} transcriptTitle="" transcriptText="text" />)
    expect(screen.getByRole('button', { name: 'Generate' })).toBeDisabled()
  })

  it('disables Generate when transcript text is empty in transcript mode', () => {
    render(<GenerateForm {...transcriptProps} transcriptTitle="Meeting" transcriptText="" />)
    expect(screen.getByRole('button', { name: 'Generate' })).toBeDisabled()
  })

  it('enables Generate when both title and transcript text are non-empty', () => {
    render(
      <GenerateForm
        {...transcriptProps}
        transcriptTitle="Q3 Meeting"
        transcriptText="Some transcript content."
      />
    )
    expect(screen.getByRole('button', { name: 'Generate' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Preview' })).toBeEnabled()
  })

  it('calls onTranscriptTitleChange when title is typed', async () => {
    const onTranscriptTitleChange = vi.fn()
    const user = userEvent.setup()
    render(<GenerateForm {...transcriptProps} onTranscriptTitleChange={onTranscriptTitleChange} />)
    await user.type(screen.getByRole('textbox', { name: /meeting title/i }), 'Q3')
    expect(onTranscriptTitleChange).toHaveBeenCalled()
  })

  it('calls onTranscriptTextChange when transcript is typed', async () => {
    const onTranscriptTextChange = vi.fn()
    const user = userEvent.setup()
    render(<GenerateForm {...transcriptProps} onTranscriptTextChange={onTranscriptTextChange} />)
    await user.type(screen.getByRole('textbox', { name: /^Transcript/i }), 'hi')
    expect(onTranscriptTextChange).toHaveBeenCalled()
  })

  it('calls onTranscriptMeetingTypeChange when meeting type dropdown changed', async () => {
    const onTranscriptMeetingTypeChange = vi.fn()
    const user = userEvent.setup()
    render(
      <GenerateForm {...transcriptProps} onTranscriptMeetingTypeChange={onTranscriptMeetingTypeChange} />
    )
    await user.selectOptions(screen.getByRole('combobox', { name: /meeting type/i }), 'eos')
    expect(onTranscriptMeetingTypeChange).toHaveBeenCalledWith('eos')
  })
})
