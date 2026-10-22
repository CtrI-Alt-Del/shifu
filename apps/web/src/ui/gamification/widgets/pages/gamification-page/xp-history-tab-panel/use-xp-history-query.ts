import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { SERVER_ENV } from '@/constants/server-env'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { XpHistory } from '@/core/gamification/xp-history'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { GamificationService } from '@/rest/services/gamification-service'

type XpHistoryResult =
  | { kind: 'success'; history: XpHistory }
  | { kind: 'unauthorized' | 'forbidden' | 'unavailable'; statusCode?: number }

export const getXpHistory = createServerFn({ method: 'GET' }).handler(
  async (): Promise<XpHistoryResult> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const gamificationService = GamificationService(
        AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
      )
      const history = await gamificationService.getXpHistory(access.accessToken)
      return { kind: 'success', history }
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

export function useXpHistoryQuery() {
  const query = useQuery({
    queryKey: ['gamification', 'xp-history'],
    retry: false,
    queryFn: async () => {
      const result = await getXpHistory()

      if (result.kind === 'success') return result.history
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
    history: query.data ?? null,
    historyError: query.error ?? null,
    isLoadingHistory: query.isPending,
    isFetchingHistory: query.isFetching,
    refetchHistory: query.refetch,
  }
}
