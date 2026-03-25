import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ArtifactList } from '../components/ArtifactList'
import type { ArtifactMetadata } from '../types'

function makeArtifact(overrides: Partial<ArtifactMetadata> = {}): ArtifactMetadata {
  return {
    artifact_id: 'art-001',
    run_id: 'run-001',
    artifact_type: 'pptx',
    filename: 'output.pptx',
    relative_path: 'run-001/output.pptx',
    mime_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    size_bytes: 1024,
    checksum: 'abc123',
    is_final_output: true,
    visibility: 'downloadable',
    retention_class: 'standard',
    status: 'present',
    created_at: '2026-03-24T10:00:00.000Z',
    ...overrides,
  }
}

describe('ArtifactList — loading state', () => {
  it('shows loading message when loading', () => {
    render(<ArtifactList artifacts={[]} loading={true} error={null} />)
    expect(screen.getByText('Loading artifacts…')).toBeInTheDocument()
  })
})

describe('ArtifactList — error state', () => {
  it('shows error message', () => {
    const err = new Error('Network error')
    render(<ArtifactList artifacts={[]} loading={false} error={err} />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Network error')
  })

  it('shows Retry button when onRetry provided', () => {
    const err = new Error('fail')
    const retry = vi.fn()
    render(<ArtifactList artifacts={[]} loading={false} error={err} onRetry={retry} />)
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})

describe('ArtifactList — empty state', () => {
  it('shows empty message when no artifacts', () => {
    render(<ArtifactList artifacts={[]} loading={false} error={null} />)
    expect(screen.getByText(/No artifacts found/)).toBeInTheDocument()
  })
})

describe('ArtifactList — artifact rendering', () => {
  it('renders artifact filename', () => {
    const a = makeArtifact({ filename: 'slide.pptx' })
    render(<ArtifactList artifacts={[a]} loading={false} error={null} />)
    expect(screen.getByText('slide.pptx')).toBeInTheDocument()
  })

  it('renders formatted size', () => {
    const a = makeArtifact({ size_bytes: 2048 })
    render(<ArtifactList artifacts={[a]} loading={false} error={null} />)
    expect(screen.getByText('2.0 KiB')).toBeInTheDocument()
  })

  it('renders download link for present downloadable artifact', () => {
    const a = makeArtifact({ status: 'present', visibility: 'downloadable' })
    render(<ArtifactList artifacts={[a]} loading={false} error={null} />)
    expect(screen.getByRole('link', { name: 'Download' })).toBeInTheDocument()
  })

  it('no download link for deleted artifact', () => {
    const a = makeArtifact({ status: 'deleted', visibility: 'downloadable' })
    render(<ArtifactList artifacts={[a]} loading={false} error={null} />)
    expect(screen.queryByRole('link', { name: 'Download' })).not.toBeInTheDocument()
  })

  it('no download link for internal artifact', () => {
    const a = makeArtifact({ status: 'present', visibility: 'internal' })
    render(<ArtifactList artifacts={[a]} loading={false} error={null} />)
    expect(screen.queryByRole('link', { name: 'Download' })).not.toBeInTheDocument()
  })
})

describe('ArtifactList — sort order', () => {
  it('sorts final output before manifest before internal', () => {
    const artifacts: ArtifactMetadata[] = [
      makeArtifact({ artifact_id: 'a1', artifact_type: 'spec_json', is_final_output: false, filename: 'spec.json', created_at: '2026-03-24T10:00:01.000Z' }),
      makeArtifact({ artifact_id: 'a2', artifact_type: 'manifest', is_final_output: false, filename: 'manifest.json', created_at: '2026-03-24T10:00:02.000Z' }),
      makeArtifact({ artifact_id: 'a3', artifact_type: 'pptx', is_final_output: true, filename: 'output.pptx', created_at: '2026-03-24T10:00:00.000Z' }),
    ]
    render(<ArtifactList artifacts={artifacts} loading={false} error={null} />)
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('output.pptx')
    expect(items[1]).toHaveTextContent('manifest.json')
    expect(items[2]).toHaveTextContent('spec.json')
  })

  it('sorts within same category by created_at DESC', () => {
    const artifacts: ArtifactMetadata[] = [
      makeArtifact({ artifact_id: 'a1', is_final_output: false, artifact_type: 'spec_json', filename: 'older.json', created_at: '2026-03-24T09:00:00.000Z' }),
      makeArtifact({ artifact_id: 'a2', is_final_output: false, artifact_type: 'spec_json', filename: 'newer.json', created_at: '2026-03-24T11:00:00.000Z' }),
    ]
    render(<ArtifactList artifacts={artifacts} loading={false} error={null} />)
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('newer.json')
    expect(items[1]).toHaveTextContent('older.json')
  })
})
