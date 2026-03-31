import type { RunDetail } from '../types'
import { RunStatusBadge } from './RunStatusBadge'
import type { RunStatus } from '../types'
import { formatDuration } from '../utils/format'

interface Props {
  a: RunDetail
  b: RunDetail
}

interface Row {
  label: string
  valueA: string | null
  valueB: string | null
}

function fmt(v: string | number | null | undefined): string | null {
  if (v == null) return null
  return String(v)
}

function buildRows(a: RunDetail, b: RunDetail): Row[] {
  return [
    { label: 'Status',        valueA: a.status,          valueB: b.status },
    { label: 'Mode',          valueA: a.mode,             valueB: b.mode },
    { label: 'Source',        valueA: a.source,           valueB: b.source },
    { label: 'Template',      valueA: fmt(a.template_id), valueB: fmt(b.template_id) },
    { label: 'Playbook',      valueA: fmt(a.playbook_id), valueB: fmt(b.playbook_id) },
    { label: 'Profile',       valueA: a.profile,          valueB: b.profile },
    { label: 'Duration',
      valueA: a.total_ms != null && a.total_ms > 0 ? formatDuration(a.total_ms) : null,
      valueB: b.total_ms != null && b.total_ms > 0 ? formatDuration(b.total_ms) : null },
    { label: 'Artifacts',     valueA: fmt(a.artifact_count), valueB: fmt(b.artifact_count) },
    { label: 'Error category',valueA: fmt(a.error_category), valueB: fmt(b.error_category) },
    { label: 'Error message', valueA: fmt(a.error_message),  valueB: fmt(b.error_message) },
  ]
}

function isDiff(row: Row): boolean {
  return row.valueA !== row.valueB
}

export function RunCompareTable({ a, b }: Props) {
  const rows = buildRows(a, b)

  return (
    <div className="run-compare">
      <table className="run-compare__table">
        <thead>
          <tr>
            <th scope="col" className="run-compare__field-col">Field</th>
            <th scope="col">
              <span title={a.run_id}>{a.run_id.substring(0, 8)}…</span>
            </th>
            <th scope="col">
              <span title={b.run_id}>{b.run_id.substring(0, 8)}…</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.label}
              className={isDiff(row) ? 'run-compare__row--diff' : undefined}
            >
              <th scope="row">{row.label}</th>
              <td>
                {row.label === 'Status' && a.status
                  ? <RunStatusBadge status={a.status as RunStatus} />
                  : (row.valueA ?? '—')}
              </td>
              <td>
                {row.label === 'Status' && b.status
                  ? <RunStatusBadge status={b.status as RunStatus} />
                  : (row.valueB ?? '—')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
