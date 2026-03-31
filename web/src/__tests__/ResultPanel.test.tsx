import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ResultPanel } from '../components/ResultPanel'
import type { GenerateResponse } from '../types'
import { clipboardWriteText } from './setup'

// ── fixtures ──────────────────────────────────────────────────────────────────

const previewResult: GenerateResponse = {
  request_id: 'req-preview-001',
  success: true,
  playbook_id: 'meeting-notes-to-eos-rocks',
  template_id: 'ops_review_v1',
  mode: 'deterministic',
  stage: 'deck_planned',
  slide_count: 3,
  slide_types: ['title', 'bullets', 'closing'],
  output_path: null,
  artifact_paths: null,
  notes: null,
}

const generateResult: GenerateResponse = {
  request_id: 'req-gen-002',
  success: true,
  playbook_id: 'ado-summary-to-weekly-delivery',
  template_id: 'ops_review_v1',
  mode: 'ai',
  stage: 'rendered',
  slide_count: 5,
  slide_types: ['title', 'bullets', 'bullets', 'bullets', 'closing'],
  output_path: '/tmp/pptgen_api/xyz/output.pptx',
  artifact_paths: { spec: '/tmp/pptgen_api/xyz/artifacts/spec.json' },
  notes: 'Generated via AI mode.',
}


// ── preview mode ──────────────────────────────────────────────────────────────

describe('ResultPanel — preview mode', () => {
  it('renders the Preview heading', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.getByRole('heading', { name: 'Preview' })).toBeInTheDocument()
  })

  it('shows request_id', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.getByText('req-preview-001')).toBeInTheDocument()
  })

  it('shows playbook_id', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.getByText('meeting-notes-to-eos-rocks')).toBeInTheDocument()
  })

  it('shows stage badge', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.getByText('deck_planned')).toBeInTheDocument()
  })

  it('shows slide count', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows slide types', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.getByText(/title.*bullets.*closing/)).toBeInTheDocument()
  })

  it('does not render output path section when null', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.queryByText('output path')).not.toBeInTheDocument()
  })
})

// ── generate mode ─────────────────────────────────────────────────────────────

describe('ResultPanel — generate mode', () => {
  it('renders the Generated heading', () => {
    render(<ResultPanel result={generateResult} mode="generate" />)
    expect(screen.getByRole('heading', { name: 'Generated' })).toBeInTheDocument()
  })

  it('shows output_path', () => {
    render(<ResultPanel result={generateResult} mode="generate" />)
    expect(screen.getByText('/tmp/pptgen_api/xyz/output.pptx')).toBeInTheDocument()
  })

  it('renders a Download .pptx link', () => {
    render(<ResultPanel result={generateResult} mode="generate" />)
    const link = screen.getByRole('link', { name: 'Download .pptx' })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('download')
  })

  it('renders a Copy path button', () => {
    render(<ResultPanel result={generateResult} mode="generate" />)
    expect(screen.getByRole('button', { name: 'Copy path' })).toBeInTheDocument()
  })

  it('shows artifact paths', () => {
    render(<ResultPanel result={generateResult} mode="generate" />)
    expect(screen.getByText('spec')).toBeInTheDocument()
    expect(screen.getByText('/tmp/pptgen_api/xyz/artifacts/spec.json')).toBeInTheDocument()
  })

  it('shows notes', () => {
    render(<ResultPanel result={generateResult} mode="generate" />)
    expect(screen.getByText('Generated via AI mode.')).toBeInTheDocument()
  })

  it('shows stage rendered badge', () => {
    render(<ResultPanel result={generateResult} mode="generate" />)
    expect(screen.getByText('rendered')).toBeInTheDocument()
  })
})

// ── copy request_id button ────────────────────────────────────────────────────

// navigator.clipboard is installed in setup.ts; reset the mock before each test.
describe('ResultPanel — copy request_id button', () => {
  beforeEach(() => {
    clipboardWriteText.mockClear()
  })

  it('renders a Copy button next to request_id', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.getByRole('button', { name: /copy request id/i })).toBeInTheDocument()
  })

  it('shows "Copy" label by default', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.getByRole('button', { name: /copy request id/i })).toHaveTextContent('Copy')
  })

  it('calls clipboard.writeText with the request_id on click', () => {
    // fireEvent.click does not install a virtual clipboard the way userEvent
    // does, so our mock in setup.ts remains in place for the assertion.
    render(<ResultPanel result={previewResult} mode="preview" />)
    fireEvent.click(screen.getByRole('button', { name: /copy request id/i }))
    expect(clipboardWriteText).toHaveBeenCalledWith('req-preview-001')
  })

  it('changes button label to "Copied!" after click', async () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    fireEvent.click(screen.getByRole('button', { name: /copy request id/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /copy request id/i })).toHaveTextContent('Copied!')
    )
  })

  it('copy button works in generate mode too', () => {
    render(<ResultPanel result={generateResult} mode="generate" />)
    fireEvent.click(screen.getByRole('button', { name: /copy request id/i }))
    expect(clipboardWriteText).toHaveBeenCalledWith('req-gen-002')
  })
})

// ── transcript mode badge ──────────────────────────────────────────────────

describe('ResultPanel — transcript mode', () => {
  const transcriptResult: GenerateResponse = {
    ...previewResult,
    playbook_id: 'transcript-intelligence',
    transcript_mode: true,
    content_intent_mode: false,
  }

  it('shows Transcript badge when transcript_mode is true', () => {
    render(<ResultPanel result={transcriptResult} mode="preview" />)
    expect(screen.getByText('Transcript')).toBeInTheDocument()
  })

  it('shows playbook_id as transcript-intelligence', () => {
    render(<ResultPanel result={transcriptResult} mode="preview" />)
    expect(screen.getByText('transcript-intelligence')).toBeInTheDocument()
  })

  it('does not show CI badge when transcript_mode is true', () => {
    render(<ResultPanel result={transcriptResult} mode="preview" />)
    expect(screen.queryByText('CI')).not.toBeInTheDocument()
  })

  it('shows CI badge when content_intent_mode is true and transcript_mode is false', () => {
    const ciResult: GenerateResponse = {
      ...previewResult,
      playbook_id: 'content-intelligence',
      content_intent_mode: true,
      transcript_mode: false,
    }
    render(<ResultPanel result={ciResult} mode="preview" />)
    expect(screen.getByText(/\bCI\b/)).toBeInTheDocument()
  })

  it('shows neither badge in raw text mode', () => {
    render(<ResultPanel result={previewResult} mode="preview" />)
    expect(screen.queryByText('CI')).not.toBeInTheDocument()
    expect(screen.queryByText(/Transcript/i)).not.toBeInTheDocument()
  })
})
