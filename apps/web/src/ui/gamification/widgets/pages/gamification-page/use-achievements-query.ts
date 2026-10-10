import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import type { AchievementsOverview } from '@/core/gamification/achievements-overview'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { GamificationService } from '@/rest/services/gamification-service'

type AchievementsResult =
  | { kind: 'success'; overview: AchievementsOverview }
  | { kind: 'unauthorized' | 'forbidden' | 'unavailable'; statusCode?: number }

const getAchievements = createServerFn({ method: 'GET' }).handler(
  async (): Promise<AchievementsResult> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const gamificationService = GamificationService(
        AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
      )
      const overview = await gamificationService.listAchievements(access.accessToken)
      return { kind: 'success', overview }
    } catch (error) {
      if (error instanceof AuthError) {
        return error.kind === 'authentication-rejected'
          ? { kind: 'unauthorized', statusCode: error.statusCode }
          : { kind: 'unavailable', statusCode: error.statusCode }
      }

      if (error instanceof RestError) {
        if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
          return { kind: 'unauthorized' }
        if (error.statusCode === HTTP_STATUS_CODE.forbidden) return { kind: 'forbidden' }
        return { kind: 'unavailable', statusCode: error.statusCode }
      }

      return { kind: 'unavailable' }
    }
  },
)

export function useAchievementsQuery() {
  const query = useQuery({
    queryKey: ['gamification', 'achievements'],
    retry: false,
    queryFn: async () => {
      const result = await getAchievements()

      if (result.kind === 'success') return result.overview
      if (result.kind === 'unauthorized' || result.kind === 'forbidden') {
        throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
          statusCode: result.statusCode,
        })
      }
      throw new RestError(
        'Serviço temporariamente indisponível.',
        result.statusCode ?? 503,
      )
    },
  })

  return {
    overview: query.data ?? null,
    overviewError: query.error ?? null,
    isLoadingOverview: query.isPending,
    isFetchingOverview: query.isFetching,
    refetchOverview: query.refetch,
  }
}
