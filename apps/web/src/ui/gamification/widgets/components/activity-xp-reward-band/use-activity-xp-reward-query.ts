import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { SERVER_ENV } from '@/constants/server-env'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { ActivityXpReward } from '@/core/gamification/activity-xp-reward'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { GamificationService } from '@/rest/services/gamification-service'

type ActivityXpRewardInput = { activityId: string; attemptId: string }

type ActivityXpRewardResult =
  | { kind: 'success'; reward: ActivityXpReward }
  | { kind: 'unauthorized' | 'not-found' | 'unavailable'; statusCode?: number }

export const POLL_INTERVAL_MS = 3000
export const MAX_POLL_ATTEMPTS = 10

export const getActivityXpReward = createServerFn({ method: 'GET' })
  .validator((input: unknown): ActivityXpRewardInput => input as ActivityXpRewardInput)
  .handler(async ({ data }): Promise<ActivityXpRewardResult> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const gamificationService = GamificationService(
        AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
      )
      const reward = await gamificationService.getActivityXpReward(
        access.accessToken,
        data.activityId,
        data.attemptId,
      )
      return { kind: 'success', reward }
    } catch (error) {
      if (error instanceof AuthError) {
        return error.kind === 'authentication-rejected'
          ? { kind: 'unauthorized', statusCode: error.statusCode }
          : { kind: 'unavailable', statusCode: error.statusCode }
      }

      if (error instanceof RestError) {
        if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
          return { kind: 'unauthorized' }
        if (error.statusCode === HTTP_STATUS_CODE.notFound) return { kind: 'not-found' }
        return { kind: 'unavailable', statusCode: error.statusCode }
      }

      return { kind: 'unavailable' }
    }
  })

export function useActivityXpRewardQuery(activityId: string, attemptId: string) {
  const queryClient = useQueryClient()
  const queryKey = ['gamification', 'activity-xp-reward', activityId, attemptId]
  const query = useQuery({
    queryKey,
    retry: false,
    queryFn: async () => {
      const result = await getActivityXpReward({ data: { activityId, attemptId } })

      if (result.kind === 'success') return result.reward
      throw new RestError(
        'Serviço temporariamente indisponível.',
        result.statusCode ?? 503,
      )
    },
    refetchInterval: (query) =>
      query.state.data?.state === 'pending' &&
      query.state.dataUpdateCount < MAX_POLL_ATTEMPTS
        ? POLL_INTERVAL_MS
        : false,
    refetchIntervalInBackground: false,
  })

  return {
    reward: query.data ?? null,
    rewardError: query.error ?? null,
    isLoadingReward: query.isPending,
    pollAttempts: queryClient.getQueryState(queryKey)?.dataUpdateCount ?? 0,
  }
}
