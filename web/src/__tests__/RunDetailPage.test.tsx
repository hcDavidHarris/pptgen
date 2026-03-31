import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { RunDetailPage } from '../pages/RunDetailPage'

function ok(body: unknown) {
  return { ok: true as const, status: 200, body }
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

const RUN_DETAIL = {
  run_id: 'run-xyz-999',
  status: 'succeeded',
  source: 'api_sync',
  job_id: null,
  request_id: 'req-001',
  mode: 'deterministic',
  template_id: 'hc-default',
  playbook_id: 'meeting-notes-to-eos-rocks',
  profile: 'dev',
  started_at: '2026-03-24T10:00:00.000Z',
  completed_at: '2026-03-24T10:00:02.500Z',
  total_ms: 2500,
  error_category: null,
  error_message: null,
  manifest_path: '/artifacts/run-xyz-999/manifest.json',
}

const RUN_METRICS = {
  run_id: 'run-xyz-999',
  total_ms: 2500,
  artifact_count: 3,
  stage_timings: [
    { stage: 'route', duration_ms: 50 },
    { stage: 'extract', duration_ms: 200 },
    { stage: 'plan', duration_ms: 800 },
    { stage: 'render', duration_ms: 1450 },
  ],
  slowest_stage: 'render',
  fastest_stage: 'route',
}

// 3 hooks fire in order: useRunDetail, useRunMetrics, useRunArtifacts
const EMPTY_ARTIFACTS: unknown[] = []

function renderPage(runId = 'run-xyz-999') {
  return render(
    <MemoryRouter initialEntries={[`/runs/${runId}`]}>
      <Routes>
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('RunDetailPage — loading', () => {
  it('shows loading indicator initially', () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    expect(screen.getByText('Loading run…')).toBeInTheDocument()
  })
})

describe('RunDetailPage — success', () => {
  it('shows run ID after load', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('run-xyz-999')).toBeInTheDocument()
    })
  })

  it('shows status badge', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('succeeded')).toBeInTheDocument()
    })
  })

  it('shows playbook ID', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('meeting-notes-to-eos-rocks')).toBeInTheDocument()
    })
  })

  it('shows stage timings table', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Stage Timings' })).toBeInTheDocument()
    })
    // 'route' and 'render' appear in both table cells and the annotation <strong>s
    expect(screen.getAllByText('route').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('plan').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('render').length).toBeGreaterThanOrEqual(1)
  })

  it('highlights slowest stage row', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument()
    })
    const table = screen.getByRole('table')
    const rows = table.querySelectorAll('tbody tr')
    const renderRow = Array.from(rows).find((r) => r.textContent?.startsWith('render'))
    expect(renderRow).toBeTruthy()
    expect(renderRow).toHaveClass('run-metrics-card__row--slowest')
  })

  it('shows back to runs link', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Back to Runs/)).toBeInTheDocument()
    })
  })
})

describe('RunDetailPage — error', () => {
  it('shows error state when run not found', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(
      { ok: false, status: 404, body: { detail: 'Run not found: run-xyz-999' } },
      ok(RUN_METRICS),
      ok(EMPTY_ARTIFACTS),
    ))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})

describe('RunDetailPage — metrics non-fatal', () => {
  it('still shows run summary when metrics fetch fails', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(
      ok(RUN_DETAIL),
      { ok: false, status: 404, body: { detail: 'Metrics not available' } },
      ok(EMPTY_ARTIFACTS),
    ))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('run-xyz-999')).toBeInTheDocument()
    })
    // Metrics section should not appear — but no blocking error
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('RunDetailPage — artifacts', () => {
  it('shows empty artifact state when no artifacts', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/No artifacts found/)).toBeInTheDocument()
    })
  })

  it('shows download CTA when final output artifact present', async () => {
    const artifacts = [{
      artifact_id: 'art-final',
      run_id: 'run-xyz-999',
      artifact_type: 'pptx',
      filename: 'output.pptx',
      relative_path: 'run-xyz-999/output.pptx',
      mime_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      size_bytes: 65536,
      checksum: 'abc',
      is_final_output: true,
      visibility: 'downloadable',
      retention_class: 'standard',
      status: 'present',
      created_at: '2026-03-24T10:00:02.000Z',
    }]
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(artifacts)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Download Presentation' })).toBeInTheDocument()
    })
  })

  it('shows manifest toggle when run has manifest_path', async () => {
    vi.stubGlobal('fetch', makeFetchQueue(ok(RUN_DETAIL), ok(RUN_METRICS), ok(EMPTY_ARTIFACTS)))
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Manifest/ })).toBeInTheDocument()
    })
  })
})
