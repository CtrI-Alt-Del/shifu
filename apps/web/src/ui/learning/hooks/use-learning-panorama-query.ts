import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { LearningPanorama } from '@/core/learning/learning-panorama'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'

type LearningPanoramaResult =
  | { kind: 'success'; panorama: LearningPanorama }
  | { kind: 'unauthorized' | 'forbidden' | 'unavailable'; statusCode?: number }

export const LEARNING_PANORAMA_QUERY_KEY = ['learning', 'panorama'] as const

export const getLearningPanorama = createServerFn({ method: 'GET' }).handler(
  async (): Promise<LearningPanoramaResult> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const learningService = LearningService(createServerRequestClient(undefined))
      const panorama = await learningService.getLearningPanorama(access.accessToken)
      return { kind: 'success', panorama }
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

export function useLearningPanoramaQuery() {
  const {
    data: panorama = null,
    error: panoramaError,
    isPending: isLoadingPanorama,
    isFetching: isFetchingPanorama,
    refetch: refetchPanorama,
  } = useQuery({
    queryKey: LEARNING_PANORAMA_QUERY_KEY,
    retry: false,
    queryFn: async () => {
      const result = await getLearningPanorama()

      if (result.kind === 'success') return result.panorama
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
    panorama,
    panoramaError,
    isLoadingPanorama,
    isFetchingPanorama,
    refetchPanorama,
  }
}
