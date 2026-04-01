import { useReducer, useEffect } from 'react'
import { fetchSystemHealth } from '../api'
import type { SystemHealth } from '../types'

type State = { health: SystemHealth | null; loading: boolean; error: Error | null }
type Action =
  | { type: 'loading' }
  | { type: 'success'; payload: SystemHealth }
  | { type: 'error'; payload: Error }

function reducer(_state: State, action: Action): State {
  switch (action.type) {
    case 'loading': return { health: null, loading: true, error: null }
    case 'success': return { health: action.payload, loading: false, error: null }
    case 'error':   return { health: null, loading: false, error: action.payload }
  }
}

export function useSystemHealth() {
  const [state, dispatch] = useReducer(reducer, { health: null, loading: true, error: null })

  useEffect(() => {
    dispatch({ type: 'loading' })
    fetchSystemHealth()
      .then((h) => dispatch({ type: 'success', payload: h }))
      .catch((err) => dispatch({ type: 'error', payload: err }))
  }, [])

  return state
}
