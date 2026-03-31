import { useEffect, useReducer } from 'react'
import type { RunMetrics } from '../types'
import { fetchRunMetrics } from '../api'

interface State {
  metrics: RunMetrics | null
  loading: boolean
  error: Error | null
}

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; metrics: RunMetrics }
  | { type: 'FETCH_ERROR'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS':
      return { metrics: action.metrics, loading: false, error: null }
    case 'FETCH_ERROR':
      // Non-fatal: preserve any previously loaded metrics
      return { ...state, loading: false, error: action.error }
  }
}

const INITIAL: State = { metrics: null, loading: false, error: null }

export function useRunMetrics(runId: string) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  useEffect(() => {
    dispatch({ type: 'FETCH_START' })
    fetchRunMetrics(runId)
      .then((metrics) => dispatch({ type: 'FETCH_SUCCESS', metrics }))
      .catch((err: unknown) =>
        dispatch({ type: 'FETCH_ERROR', error: err instanceof Error ? err : new Error(String(err)) })
      )
  }, [runId])

  return state
}
