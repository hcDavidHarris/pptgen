import type { TemplateVersionDetail, TemplateVersionWithGovernance } from '../types'

type AnyVersion = TemplateVersionDetail | TemplateVersionWithGovernance

function hasGovernance(v: AnyVersion): v is TemplateVersionWithGovernance {
  return 'is_default' in v
}

interface Props {
  versions: AnyVersion[]
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
        {[...versions].reverse().map((v) => {
          const isDefault = hasGovernance(v) && v.is_default
          const isDeprecated = hasGovernance(v) && v.deprecated_at != null

          return (
            <tr
              key={v.version}
              className={`template-version-table__row${isDeprecated ? ' template-version-table__row--deprecated' : ''}`}
            >
              <td>
                <code>{v.version}</code>
                {isDefault && (
                  <span className="version-badge version-badge--default" aria-label="default version">
                    default
                  </span>
                )}
                {isDeprecated && (
                  <span className="version-badge version-badge--deprecated" aria-label="deprecated version">
                    deprecated
                  </span>
                )}
              </td>
              <td>
                <code className="template-version-table__hash" title={v.template_revision_hash}>
                  {v.template_revision_hash}
                </code>
              </td>
              <td>{v.ai_mode}</td>
              <td>{v.input_contract_version ?? '—'}</td>
              <td>{v.playbook_path ?? '—'}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
