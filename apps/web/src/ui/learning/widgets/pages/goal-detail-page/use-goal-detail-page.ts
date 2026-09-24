import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import type { GoalDetail } from '@/core/learning/goal-detail'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

type ActionResult = GoalDetail | { kind: 'unauthorized' | 'not-found' | 'unavailable' }

export const getGoalDetailAction = createServerFn({ method: 'GET' })
  .validator((goalId: string) => goalId)
  .handler(async ({ data: goalId }): Promise<ActionResult> => {
    if (!COMPETENCY_DETAIL_ID_PATTERN.test(goalId)) return { kind: 'not-found' }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).getGoalDetail(access.accessToken, goalId)
    } catch (error) {
      if (error instanceof RestError && error.statusCode === 401)
        return { kind: 'unauthorized' }
      if (error instanceof RestError && error.statusCode === 404)
        return { kind: 'not-found' }
      return { kind: 'unavailable' }
    }
  })

export function useGoalDetailPage(goalId: string) {
  const { navigateTo } = useNavigation()
  const query = useQuery({
    queryKey: ['learning', 'goal-detail', goalId],
    queryFn: async () => {
      const result = await getGoalDetailAction({ data: goalId })
      if ('kind' in result) {
        if (result.kind === 'unauthorized')
          throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
            statusCode: 401,
          })
        throw new RestError(
          'Objetivo indisponível.',
          result.kind === 'not-found' ? 404 : 503,
        )
      }
      return result
    },
    retry: false,
  })

  useEffect(() => {
    if (query.error instanceof AuthError) void navigateTo('login')
  }, [query.error, navigateTo])

  return {
    goal: query.data ?? null,
    isLoading: query.isPending,
    isPrivateAbsence: query.error instanceof RestError && query.error.statusCode === 404,
    isRecoverableError: Boolean(query.error) && !(query.error instanceof AuthError),
    handleRetry: query.refetch,
  }
}
