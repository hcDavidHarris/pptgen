import type { TemplateVersionDetail } from '../types'

interface Props {
  versions: TemplateVersionDetail[]
}

export function TemplateVersionList({ versions }: Props) {
  if (versions.length === 0) {
    return <p className="template-version-list__empty">No versions registered.</p>
  }

  return (
    <table className="template-version-table">
      <thead>
        <tr>
          <th scope="col">Version</th>
          <th scope="col">Revision Hash</th>
          <th scope="col">AI Mode</th>
          <th scope="col">Input Contract</th>
          <th scope="col">Playbook Path</th>
        </tr>
      </thead>
      <tbody>
        {[...versions].reverse().map((v) => (
          <tr key={v.version} className="template-version-table__row">
            <td><code>{v.version}</code></td>
            <td>
              <code className="template-version-table__hash" title={v.template_revision_hash}>
                {v.template_revision_hash}
              </code>
            </td>
            <td>{v.ai_mode}</td>
            <td>{v.input_contract_version ?? '—'}</td>
            <td>{v.playbook_path ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
