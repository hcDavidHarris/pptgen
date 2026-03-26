import { useCallback, useEffect, useReducer } from 'react'
import type {
  DeprecateVersionRequest,
  GovernanceActionResponse,
  GovernanceAuditEvent,
  GovernanceState,
  LifecycleChangeRequest,
  PromoteVersionRequest,
  TemplateVersionWithGovernance,
} from '../types'
import {
  changeLifecycle,
  deprecateVersion,
  fetchGovernanceAudit,
  fetchGovernanceState,
  fetchTemplateVersionsWithGovernance,
  promoteVersion,
} from '../api'

interface State {
  versions: TemplateVersionWithGovernance[]
  governance: GovernanceState | null
  audit: GovernanceAuditEvent[]
  loading: boolean
  error: Error | null
  actionPending: boolean
  actionError: Error | null
}

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; versions: TemplateVersionWithGovernance[]; governance: GovernanceState; audit: GovernanceAuditEvent[] }
  | { type: 'FETCH_ERROR'; error: Error }
  | { type: 'ACTION_START' }
  | { type: 'ACTION_SUCCESS'; versions: TemplateVersionWithGovernance[]; governance: GovernanceState; audit: GovernanceAuditEvent[] }
  | { type: 'ACTION_ERROR'; error: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS':
      return { ...state, loading: false, error: null, versions: action.versions, governance: action.governance, audit: action.audit }
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.error }
    case 'ACTION_START':
      return { ...state, actionPending: true, actionError: null }
    case 'ACTION_SUCCESS':
      return { ...state, actionPending: false, actionError: null, versions: action.versions, governance: action.governance, audit: action.audit }
    case 'ACTION_ERROR':
      return { ...state, actionPending: false, actionError: action.error }
  }
}

const INITIAL: State = {
  versions: [],
  governance: null,
  audit: [],
  loading: false,
  error: null,
  actionPending: false,
  actionError: null,
}

async function _reload(templateId: string) {
  return Promise.all([
    fetchTemplateVersionsWithGovernance(templateId),
    fetchGovernanceState(templateId),
    fetchGovernanceAudit(templateId),
  ])
}

export function useGovernance(templateId: string) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  useEffect(() => {
    dispatch({ type: 'FETCH_START' })
    _reload(templateId)
      .then(([versions, governance, audit]) =>
        dispatch({ type: 'FETCH_SUCCESS', versions, governance, audit })
      )
      .catch((err: unknown) =>
        dispatch({ type: 'FETCH_ERROR', error: err instanceof Error ? err : new Error(String(err)) })
      )
  }, [templateId])

  const promote = useCallback(async (version: string, body: PromoteVersionRequest): Promise<GovernanceActionResponse | null> => {
    dispatch({ type: 'ACTION_START' })
    try {
      const result = await promoteVersion(templateId, version, body)
      const [versions, governance, audit] = await _reload(templateId)
      dispatch({ type: 'ACTION_SUCCESS', versions, governance, audit })
      return result
    } catch (err: unknown) {
      const error = err instanceof Error ? err : new Error(String(err))
      dispatch({ type: 'ACTION_ERROR', error })
      return null
    }
  }, [templateId])

  const deprecate = useCallback(async (version: string, body: DeprecateVersionRequest): Promise<GovernanceActionResponse | null> => {
    dispatch({ type: 'ACTION_START' })
    try {
      const result = await deprecateVersion(templateId, version, body)
      const [versions, governance, audit] = await _reload(templateId)
      dispatch({ type: 'ACTION_SUCCESS', versions, governance, audit })
      return result
    } catch (err: unknown) {
      const error = err instanceof Error ? err : new Error(String(err))
      dispatch({ type: 'ACTION_ERROR', error })
      return null
    }
  }, [templateId])

  const setLifecycle = useCallback(async (body: LifecycleChangeRequest): Promise<GovernanceActionResponse | null> => {
    dispatch({ type: 'ACTION_START' })
    try {
      const result = await changeLifecycle(templateId, body)
      const [versions, governance, audit] = await _reload(templateId)
      dispatch({ type: 'ACTION_SUCCESS', versions, governance, audit })
      return result
    } catch (err: unknown) {
      const error = err instanceof Error ? err : new Error(String(err))
      dispatch({ type: 'ACTION_ERROR', error })
      return null
    }
  }, [templateId])

  return { ...state, promote, deprecate, setLifecycle }
}
