import { useNavigate } from 'react-router-dom'
import type { TemplateDetail } from '../types'

interface Props {
  templates: TemplateDetail[]
}

function lifecycleBadgeClass(status: string): string {
  switch (status) {
    case 'approved': return 'lifecycle-badge lifecycle-badge--approved'
    case 'review':   return 'lifecycle-badge lifecycle-badge--review'
    case 'draft':    return 'lifecycle-badge lifecycle-badge--draft'
    case 'deprecated': return 'lifecycle-badge lifecycle-badge--deprecated'
    default: return 'lifecycle-badge'
  }
}

export function TemplateTable({ templates }: Props) {
  const navigate = useNavigate()

  function handleRowClick(templateId: string) {
    navigate(`/templates/${templateId}`)
  }

  function handleRowKeyDown(e: React.KeyboardEvent, templateId: string) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      navigate(`/templates/${templateId}`)
    }
  }

  return (
    <table className="template-table">
      <thead>
        <tr>
          <th scope="col">Name</th>
          <th scope="col">Template ID</th>
          <th scope="col">Owner</th>
          <th scope="col">Status</th>
          <th scope="col">Latest Version</th>
        </tr>
      </thead>
      <tbody>
        {templates.map((t) => {
          const latestVersion = t.versions.length > 0
            ? t.versions[t.versions.length - 1]
            : '—'
          return (
            <tr
              key={t.template_id}
              className="template-table__row"
              onClick={() => handleRowClick(t.template_id)}
              onKeyDown={(e) => handleRowKeyDown(e, t.template_id)}
              tabIndex={0}
              role="button"
              aria-label={`View template ${t.name}`}
            >
              <td className="template-table__name">{t.name}</td>
              <td className="template-table__id">
                <code>{t.template_id}</code>
              </td>
              <td>{t.owner ?? '—'}</td>
              <td>
                <span className={lifecycleBadgeClass(t.lifecycle_status)}>
                  {t.lifecycle_status}
                </span>
              </td>
              <td>{latestVersion}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
