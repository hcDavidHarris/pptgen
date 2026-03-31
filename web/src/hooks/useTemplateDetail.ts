import { useEffect, useReducer } from 'react'
import type { TemplateDetail, TemplateVersionDetail } from '../types'
import { fetchTemplateDetail, fetchTemplateVersions } from '../api'

interface State {
  template: TemplateDetail | null
  versions: TemplateVersionDetail[]
  loading: boolean
  error: Error | null
}

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; template: TemplateDetail; versions: TemplateVersionDetail[] }
  | { type: 'FETCH_ERROR'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS':
      return { template: action.template, versions: action.versions, loading: false, error: null }
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.error }
  }
}

const INITIAL: State = { template: null, versions: [], loading: false, error: null }

export function useTemplateDetail(templateId: string) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  useEffect(() => {
    dispatch({ type: 'FETCH_START' })
    Promise.all([fetchTemplateDetail(templateId), fetchTemplateVersions(templateId)])
      .then(([template, versions]) =>
        dispatch({ type: 'FETCH_SUCCESS', template, versions })
      )
      .catch((err: unknown) =>
        dispatch({ type: 'FETCH_ERROR', error: err instanceof Error ? err : new Error(String(err)) })
      )
  }, [templateId])

  return state
}
