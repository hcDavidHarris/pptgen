import { useEffect, useReducer } from 'react'
import type { RunDetail } from '../types'
import { fetchRun } from '../api'

interface State {
  run: RunDetail | null
  loading: boolean
  error: Error | null
}

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; run: RunDetail }
  | { type: 'FETCH_ERROR'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS':
      return { run: action.run, loading: false, error: null }
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.error }
  }
}

const INITIAL: State = { run: null, loading: false, error: null }

export function useRunDetail(runId: string) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  useEffect(() => {
    dispatch({ type: 'FETCH_START' })
    fetchRun(runId)
      .then((run) => dispatch({ type: 'FETCH_SUCCESS', run }))
      .catch((err: unknown) =>
        dispatch({ type: 'FETCH_ERROR', error: err instanceof Error ? err : new Error(String(err)) })
      )
  }, [runId])

  return state
}
