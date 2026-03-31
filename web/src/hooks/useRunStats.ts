import { useReducer, useEffect } from 'react'
import { fetchRunStats } from '../api'
import type { RunStats } from '../types'

type State = { stats: RunStats | null; loading: boolean; error: Error | null }
type Action =
  | { type: 'loading' }
  | { type: 'success'; payload: RunStats }
  | { type: 'error'; payload: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'loading': return { stats: null, loading: true, error: null }
    case 'success': return { stats: action.payload, loading: false, error: null }
    case 'error':   return { stats: null, loading: false, error: action.payload }
  }
}

export function useRunStats(window = '24h') {
  const [state, dispatch] = useReducer(reducer, { stats: null, loading: true, error: null })

  useEffect(() => {
    dispatch({ type: 'loading' })
    fetchRunStats(window)
      .then((s) => dispatch({ type: 'success', payload: s }))
      .catch((err) => dispatch({ type: 'error', payload: err }))
  }, [window])

  return state
}
