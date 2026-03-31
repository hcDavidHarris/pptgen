import { useEffect, useReducer } from 'react'
import type { ArtifactMetadata } from '../types'
import { fetchRunArtifacts } from '../api'

interface State {
  artifacts: ArtifactMetadata[]
  loading: boolean
  error: Error | null
}

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; artifacts: ArtifactMetadata[] }
  | { type: 'FETCH_ERROR'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS':
      return { artifacts: action.artifacts, loading: false, error: null }
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.error }
  }
}

const INITIAL: State = { artifacts: [], loading: false, error: null }

export function useRunArtifacts(runId: string) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  useEffect(() => {
    dispatch({ type: 'FETCH_START' })
    fetchRunArtifacts(runId)
      .then((artifacts) => dispatch({ type: 'FETCH_SUCCESS', artifacts }))
      .catch((err: unknown) =>
        dispatch({ type: 'FETCH_ERROR', error: err instanceof Error ? err : new Error(String(err)) })
      )
  }, [runId])

  return state
}
