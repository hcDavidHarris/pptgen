import { useEffect, useReducer } from 'react'
import type { TemplateUsageSummary, TemplateVersionUsageItem, TemplateUsageTrendItem } from '../types'
import {
  fetchTemplateAnalyticsSummary,
  fetchTemplateAnalyticsVersions,
  fetchTemplateAnalyticsTrend,
} from '../api'

interface State {
  summary: TemplateUsageSummary | null
  versions: TemplateVersionUsageItem[]
  trend: TemplateUsageTrendItem[]
  loading: boolean
  error: Error | null
}

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; summary: TemplateUsageSummary; versions: TemplateVersionUsageItem[]; trend: TemplateUsageTrendItem[] }
  | { type: 'FETCH_ERROR'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS':
      return { summary: action.summary, versions: action.versions, trend: action.trend, loading: false, error: null }
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.error }
  }
}

const INITIAL: State = { summary: null, versions: [], trend: [], loading: false, error: null }

export function useTemplateAnalytics(templateId: string, days = 30) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  useEffect(() => {
    dispatch({ type: 'FETCH_START' })
    Promise.all([
      fetchTemplateAnalyticsSummary(templateId, days),
      fetchTemplateAnalyticsVersions(templateId, days),
      fetchTemplateAnalyticsTrend(templateId, days),
    ])
      .then(([summaryRes, versionsRes, trendRes]) =>
        dispatch({
          type: 'FETCH_SUCCESS',
          summary: summaryRes,
          versions: versionsRes.versions,
          trend: trendRes.trend,
        })
      )
      .catch((err: unknown) =>
        dispatch({ type: 'FETCH_ERROR', error: err instanceof Error ? err : new Error(String(err)) })
      )
  }, [templateId, days])

  return state
}
