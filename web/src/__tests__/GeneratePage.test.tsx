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
