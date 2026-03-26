import { useCallback, useEffect, useReducer } from 'react'
import type { FetchTemplateRunsParams, TemplateRunItem } from '../types'
import { fetchTemplateRuns } from '../api'

interface State {
  runs: TemplateRunItem[]
  loading: boolean
  error: Error | null
}

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; runs: TemplateRunItem[] }
  | { type: 'FETCH_ERROR'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS':
      return { runs: action.runs, loading: false, error: null }
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.error }
  }
}

const INITIAL: State = { runs: [], loading: false, error: null }

export function useTemplateRuns(templateId: string, params: FetchTemplateRunsParams = {}) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  const load = useCallback(async () => {
    dispatch({ type: 'FETCH_START' })
    try {
      const resp = await fetchTemplateRuns(templateId, params)
      dispatch({ type: 'FETCH_SUCCESS', runs: resp.runs })
    } catch (err) {
      dispatch({ type: 'FETCH_ERROR', error: err instanceof Error ? err : new Error(String(err)) })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templateId, JSON.stringify(params)])

  useEffect(() => {
    load()
  }, [load])

  return { ...state, refresh: load }
}
