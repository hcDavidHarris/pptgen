import { useSearchParams, Link } from 'react-router-dom'
import { useRunCompare } from '../hooks/useRunCompare'
import { RunCompareTable } from '../components/RunCompareTable'
import { ErrorState } from '../components/ErrorState'

export function RunComparePage() {
  const [params] = useSearchParams()
  const idA = params.get('a')
  const idB = params.get('b')

  const { data, loading, error } = useRunCompare(idA, idB)

  if (!idA || !idB) {
    return (
      <main className="page-container">
        <p className="run-compare__missing">Two run IDs are required. Use <code>?a=&lt;id&gt;&amp;b=&lt;id&gt;</code>.</p>
        <Link to="/runs" className="btn btn--secondary btn--small">Back to Runs</Link>
      </main>
    )
  }

  return (
    <main className="page-container">
      <div className="page-toolbar">
        <h2>Compare Runs</h2>
        <Link to="/runs" className="btn btn--secondary btn--small">Back to Runs</Link>
      </div>

      {loading && <p className="run-compare__loading">Loading…</p>}

      {error && !loading && <ErrorState error={error} />}

      {data && !loading && (
        <RunCompareTable a={data.a} b={data.b} />
      )}
    </main>
  )
}
