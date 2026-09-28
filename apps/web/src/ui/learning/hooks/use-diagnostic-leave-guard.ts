import { useEffect, useRef } from 'react'
import { useBlocker } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { clearDiagnosticRun } from '@/ui/learning/diagnostic-run-session'

type DiagnosticLeaveInput = {
  goalId: string
  skillId: string
  diagnosticRunId: string
}

type DiagnosticLeaveResult = { kind: 'success' | 'stale' | 'unavailable' }

const HTTP_CONFLICT_STATUS_CODE = 409

export const abandonDiagnosticAction = createServerFn({ method: 'POST' })
  .validator((input: DiagnosticLeaveInput) => input)
  .handler(async ({ data }): Promise<DiagnosticLeaveResult> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unavailable' }
      await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).abandonDiagnostic(
        access.accessToken,
        data.goalId,
        data.skillId,
        data.diagnosticRunId,
      )
      return { kind: 'success' }
    } catch (error) {
      if (error instanceof AuthError) return { kind: 'unavailable' }
      if (error instanceof RestError && error.statusCode === HTTP_CONFLICT_STATUS_CODE) {
        return { kind: 'stale' }
      }
      return { kind: 'unavailable' }
    }
  })

export type DiagnosticLeaveGuardProps = DiagnosticLeaveInput & {
  isActive: boolean
}

export function useDiagnosticLeaveGuard({
  goalId,
  skillId,
  diagnosticRunId,
  isActive,
}: DiagnosticLeaveGuardProps) {
  const isResolvingRef = useRef(false)
  const blocker = useBlocker({
    withResolver: true,
    enableBeforeUnload: isActive,
    shouldBlockFn: ({ next }) =>
      isActive && !isSameSkillPath(next.pathname, goalId, skillId),
  })

  useEffect(() => {
    if (blocker.status !== 'blocked' || isResolvingRef.current) return
    if (
      !window.confirm('Seu avanço diagnóstico será descartado se você sair. Deseja sair?')
    ) {
      blocker.reset()
      return
    }
    isResolvingRef.current = true
    void abandonDiagnosticAction({ data: { goalId, skillId, diagnosticRunId } })
      .then((result) => {
        if (result.kind === 'unavailable') {
          window.alert('Não foi possível descartar o diagnóstico. Tente novamente.')
          blocker.reset()
          return
        }
        clearDiagnosticRun(goalId, skillId)
        if (result.kind === 'stale') {
          window.alert('Outra aba iniciou uma nova execução do diagnóstico.')
        }
        blocker.proceed()
      })
      .catch(() => {
        window.alert('Não foi possível descartar o diagnóstico. Tente novamente.')
        blocker.reset()
      })
      .finally(() => {
        isResolvingRef.current = false
      })
  }, [blocker, diagnosticRunId, goalId, skillId])
}

function isSameSkillPath(pathname: string, goalId: string, skillId: string) {
  const [moduleName, resourceName, currentGoalId, collectionName, currentSkillId] =
    pathname.split('/').filter(Boolean)
  return (
    moduleName === 'learning' &&
    resourceName === 'goals' &&
    currentGoalId === goalId &&
    collectionName === 'skills' &&
    currentSkillId === skillId
  )
}
