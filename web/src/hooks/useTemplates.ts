import { useCallback, useEffect, useReducer } from 'react'
import type { TemplateDetail } from '../types'
import { fetchTemplateDetail, fetchTemplates } from '../api'

interface State {
  templates: TemplateDetail[]
  loading: boolean
  error: Error | null
}

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; templates: TemplateDetail[] }
  | { type: 'FETCH_ERROR'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS':
      return { templates: action.templates, loading: false, error: null }
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.error }
  }
}

const INITIAL: State = { templates: [], loading: false, error: null }

export function useTemplates() {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  const load = useCallback(async () => {
    dispatch({ type: 'FETCH_START' })
    try {
      // Fetch the list of IDs, then resolve each to a TemplateDetail
      const ids = await fetchTemplates()
      const details = await Promise.all(ids.map((id) => fetchTemplateDetail(id)))
      dispatch({ type: 'FETCH_SUCCESS', templates: details })
    } catch (err) {
      dispatch({ type: 'FETCH_ERROR', error: err instanceof Error ? err : new Error(String(err)) })
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return { ...state, refresh: load }
}
