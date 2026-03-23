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
}

describe('GenerateForm', () => {
  it('renders the textarea', () => {
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
})
