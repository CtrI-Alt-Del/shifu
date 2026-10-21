import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { SERVER_ENV } from '@/constants/server-env'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { GamificationOverview } from '@/core/gamification/overview'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { GamificationService } from '@/rest/services/gamification-service'

type OverviewResult =
  | { kind: 'success'; overview: GamificationOverview }
  | { kind: 'unauthorized' | 'forbidden' | 'unavailable'; statusCode?: number }

const getOverview = createServerFn({ method: 'GET' }).handler(
  async (): Promise<OverviewResult> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const gamificationService = GamificationService(
        AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
      )
      const overview = await gamificationService.getOverview(access.accessToken)
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

export function useOverviewQuery() {
  const {
    data: overview = null,
    error: overviewError,
    isPending: isLoadingOverview,
    isFetching: isFetchingOverview,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: ['gamification', 'overview'],
    retry: false,
    queryFn: async () => {
      const result = await getOverview()

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
    overview,
    overviewError,
    isLoadingOverview,
    isFetchingOverview,
    refetchOverview,
  }
}
