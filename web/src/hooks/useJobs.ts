import { useReducer, useEffect } from 'react'
import { fetchJobs } from '../api'
import type { JobListItem, FetchJobsParams } from '../types'

interface State {
  jobs: JobListItem[]
  loading: boolean
  error: Error | null
}

type Action =
  | { type: 'loading' }
  | { type: 'success'; jobs: JobListItem[] }
  | { type: 'error'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'loading': return { ...state, loading: true, error: null }
    case 'success': return { jobs: action.jobs, loading: false, error: null }
    case 'error': return { ...state, loading: false, error: action.error }
  }
}

const initial: State = { jobs: [], loading: false, error: null }

export function useJobs(params: FetchJobsParams = {}) {
  const [state, dispatch] = useReducer(reducer, initial)
  const { limit, offset, status } = params

  function load() {
    dispatch({ type: 'loading' })
    fetchJobs({ limit, offset, status })
      .then((r) => dispatch({ type: 'success', jobs: r.jobs }))
      .catch((err) => dispatch({ type: 'error', error: err instanceof Error ? err : new Error(String(err)) }))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limit, offset, status])

  return { ...state, refresh: load }
}
