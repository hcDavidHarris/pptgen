import { useReducer, useEffect } from 'react'
import { fetchRunPair } from '../api'
import type { RunCompareData } from '../types'

type State = { data: RunCompareData | null; loading: boolean; error: Error | null }
type Action =
  | { type: 'loading' }
  | { type: 'success'; payload: RunCompareData }
  | { type: 'error'; payload: Error }

function reducer(_state: State, action: Action): State {
  switch (action.type) {
    case 'loading': return { data: null, loading: true, error: null }
    case 'success': return { data: action.payload, loading: false, error: null }
    case 'error':   return { data: null, loading: false, error: action.payload }
  }
}

export function useRunCompare(idA: string | null, idB: string | null) {
  const [state, dispatch] = useReducer(reducer, { data: null, loading: true, error: null })

  useEffect(() => {
    if (!idA || !idB) {
      dispatch({ type: 'error', payload: new Error('Two run IDs are required') })
      return
    }
    dispatch({ type: 'loading' })
    fetchRunPair(idA, idB)
      .then((d) => dispatch({ type: 'success', payload: d }))
      .catch((err) => dispatch({ type: 'error', payload: err }))
  }, [idA, idB])

  return state
}
