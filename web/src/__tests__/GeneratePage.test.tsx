import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { GeneratePage } from '../pages/GeneratePage'

// ── fetch mock helpers ────────────────────────────────────────────────────────

const TEMPLATES_RESPONSE = {
  request_id: 'tpl-001',
  templates: ['ops_review_v1', 'architecture_overview_v1'],
}

const PREVIEW_RESPONSE = {
  request_id: 'prev-001',
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

const GENERATE_RESPONSE = {
  request_id: 'gen-001',
  success: true,
  playbook_id: 'meeting-notes-to-eos-rocks',
  template_id: 'ops_review_v1',
  mode: 'deterministic',
  stage: 'rendered',
  slide_count: 3,
  slide_types: ['title', 'bullets', 'closing'],
  output_path: '/tmp/pptgen_api/abc/output.pptx',
  artifact_paths: null,
  notes: null,
}

const TRANSCRIPT_GENERATE_RESPONSE = {
  request_id: 'transcript-gen-001',
  success: true,
  playbook_id: 'transcript-intelligence',
  template_id: null,
  mode: 'deterministic',
  stage: 'rendered',
  slide_count: 5,
  slide_types: ['title', 'bullets', 'bullets', 'bullets', 'closing'],
  output_path: '/tmp/pptgen_api/transcript-001/output.pptx',
  artifact_paths: null,
  notes: null,
  transcript_mode: true,
  content_intent_mode: false,
}

function makeFetchQueue(...responses: Array<{ ok: boolean; status: number; body: unknown }>) {
  let index = 0
  return vi.fn().mockImplementation(() => {
    const r = responses[index] ?? responses[responses.length - 1]
    index++
    return Promise.resolve({
      ok: r.ok,
      status: r.status,
      json: () => Promise.resolve(r.body),
    })
  })
}

function ok(body: unknown) {
  return { ok: true, status: 200, body }
}

function renderPage() {
  return render(
    <MemoryRouter>
      <GeneratePage />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

// ── tests ─────────────────────────────────────────────────────────────────────

describe('GeneratePage — initial render', () => {
  it('renders the Input section heading', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    renderPage()
    expect(screen.getByRole('heading', { name: 'Input' })).toBeInTheDocument()
  })

  it('loads templates from the API on mount', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'ops_review_v1' })).toBeInTheDocument()
    })
  })

  it('renders Preview and Generate buttons', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    renderPage()
    expect(screen.getByRole('button', { name: 'Preview' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate' })).toBeInTheDocument()
  })
})

describe('GeneratePage — preview flow', () => {
  it('shows preview metadata after clicking Preview', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE), ok(PREVIEW_RESPONSE)))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByRole('textbox'), 'Meeting notes here.')
    await user.click(screen.getByRole('button', { name: 'Preview' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Preview' })).toBeInTheDocument()
    })
    expect(screen.getByText('prev-001')).toBeInTheDocument()
    expect(screen.getByText('meeting-notes-to-eos-rocks')).toBeInTheDocument()
    expect(screen.getByText('deck_planned')).toBeInTheDocument()
  })

  it('shows slide count in preview', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE), ok(PREVIEW_RESPONSE)))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByRole('textbox'), 'Meeting notes here.')
    await user.click(screen.getByRole('button', { name: 'Preview' }))

    await waitFor(() => screen.getByText('3'))
    expect(screen.getByText('3')).toBeInTheDocument()
  })
})

describe('GeneratePage — generate flow', () => {
  it('shows generate metadata and output path after clicking Generate', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE), ok(GENERATE_RESPONSE)))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByRole('textbox'), 'Meeting notes here.')
    await user.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Generated' })).toBeInTheDocument()
    })
    expect(screen.getByText('gen-001')).toBeInTheDocument()
    expect(screen.getByText('rendered')).toBeInTheDocument()
    expect(screen.getByText('/tmp/pptgen_api/abc/output.pptx')).toBeInTheDocument()
  })

  it('renders Download .pptx link after generation', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE), ok(GENERATE_RESPONSE)))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByRole('textbox'), 'Meeting notes here.')
    await user.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() =>
      expect(screen.getByRole('link', { name: 'Download .pptx' })).toBeInTheDocument()
    )
  })
})

describe('GeneratePage — error handling', () => {
  it('displays API error message on generate failure', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(
      ok(TEMPLATES_RESPONSE),
      { ok: false, status: 400, body: { detail: { error: 'Unknown mode', request_id: 'err-xyz' } } },
    ))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByRole('textbox'), 'Some text.')
    await user.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() => screen.getByRole('alert'))
    expect(screen.getByRole('alert')).toHaveTextContent('Unknown mode')
    expect(screen.getByRole('alert')).toHaveTextContent('err-xyz')
  })

  it('shows no result panel after an error', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(
      ok(TEMPLATES_RESPONSE),
      { ok: false, status: 400, body: { detail: 'bad request' } },
    ))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByRole('textbox'), 'Some text.')
    await user.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() => screen.getByRole('alert'))
    expect(screen.queryByRole('heading', { name: 'Generated' })).not.toBeInTheDocument()
  })

  it('still renders the form after an error', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(
      ok(TEMPLATES_RESPONSE),
      { ok: false, status: 503, body: { detail: 'service unavailable' } },
    ))
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByRole('textbox'), 'Some text.')
    await user.click(screen.getByRole('button', { name: 'Preview' }))

    await waitFor(() => screen.getByRole('alert'))
    expect(screen.getByRole('button', { name: 'Preview' })).toBeInTheDocument()
  })
})

describe('GeneratePage — validation', () => {
  it('prevents submission when text is empty', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    renderPage()
    await waitFor(() => screen.getByRole('textbox'))

    expect(screen.getByRole('button', { name: 'Preview' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Generate' })).toBeDisabled()
  })
})

describe('GeneratePage — transcript mode', () => {
  it('renders Transcript radio button', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    renderPage()
    await waitFor(() => screen.getByRole('radio', { name: 'Transcript' }))
    expect(screen.getByRole('radio', { name: 'Transcript' })).toBeInTheDocument()
  })

  it('shows transcript fields when Transcript mode is selected', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('radio', { name: 'Transcript' }))

    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: /meeting title/i })).toBeInTheDocument()
    )
    expect(screen.getByRole('textbox', { name: /^Transcript/i })).toBeInTheDocument()
  })

  it('hides raw textarea when Transcript mode is selected', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('radio', { name: 'Transcript' }))

    await waitFor(() =>
      expect(screen.queryByRole('textbox', { name: /raw input text/i })).not.toBeInTheDocument()
    )
  })

  it('Generate button disabled when transcript title is empty', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE)))
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('radio', { name: 'Transcript' }))
    await waitFor(() => screen.getByRole('textbox', { name: /meeting title/i }))

    // Only fill transcript text, leave title empty
    await user.type(screen.getByRole('textbox', { name: /^Transcript/i }), 'Meeting content.')

    expect(screen.getByRole('button', { name: 'Generate' })).toBeDisabled()
  })

  it('shows transcript badge after transcript generate', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(TEMPLATES_RESPONSE), ok(TRANSCRIPT_GENERATE_RESPONSE)))
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('radio', { name: 'Transcript' }))
    await waitFor(() => screen.getByRole('textbox', { name: /meeting title/i }))

    await user.type(screen.getByRole('textbox', { name: /meeting title/i }), 'Q3 Meeting')
    await user.type(
      screen.getByRole('textbox', { name: /^Transcript/i }),
      'We discussed strategy and priorities.'
    )
    await user.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Generated' })).toBeInTheDocument()
    )
    expect(screen.getByText('transcript-intelligence')).toBeInTheDocument()
    expect(screen.getByText('Transcript', { selector: 'span' })).toBeInTheDocument()
  })

  it('sends transcript_payload and empty text in fetch body', async () => {
    const fetchSpy = makeFetchQueue(ok(TEMPLATES_RESPONSE), ok(TRANSCRIPT_GENERATE_RESPONSE))
    vi.stubGlobal('fetch', fetchSpy)
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('radio', { name: 'Transcript' }))
    await waitFor(() => screen.getByRole('textbox', { name: /meeting title/i }))

    await user.type(screen.getByRole('textbox', { name: /meeting title/i }), 'Leadership Sync')
    await user.type(
      screen.getByRole('textbox', { name: /^Transcript/i }),
      'Transcript content here.'
    )
    await user.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Generated' })).toBeInTheDocument()
    )

    // The second fetch call is the generate call
    const generateCall = fetchSpy.mock.calls[1]
    const body = JSON.parse(generateCall[1].body as string)
    expect(body.text).toBe('')
    expect(body.transcript_payload).toBeDefined()
    expect(body.transcript_payload.title).toBe('Leadership Sync')
    expect(body.transcript_payload.content).toBe('Transcript content here.')
  })
})
