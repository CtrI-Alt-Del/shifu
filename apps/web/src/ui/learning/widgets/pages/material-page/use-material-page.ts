import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import type { MaterialDetail } from '@/core/learning/material-detail'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type MaterialPageProps = {
  goalId: string
  skillId: string
  competencyId: string
  materialId: string
}

type ActionResult =
  | MaterialDetail
  | { kind: 'unauthorized' | 'not-found' | 'unavailable' }

export const getMaterialAction = createServerFn({ method: 'GET' })
  .validator((input: MaterialPageProps) => input)
  .handler(async ({ data }): Promise<ActionResult> => {
    if (!Object.values(data).every((value) => COMPETENCY_DETAIL_ID_PATTERN.test(value))) {
      return { kind: 'not-found' }
    }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).getMaterialDetail(access.accessToken, data)
    } catch (error) {
      if (error instanceof RestError && error.statusCode === 401) {
        return { kind: 'unauthorized' }
      }
      if (error instanceof RestError && error.statusCode === 404) {
        return { kind: 'not-found' }
      }
      return { kind: 'unavailable' }
    }
  })

export function useMaterialPage(props: MaterialPageProps) {
  const { navigateTo } = useNavigation()
  const query = useQuery({
    queryKey: [
      'learning',
      'material',
      props.goalId,
      props.skillId,
      props.competencyId,
      props.materialId,
    ],
    queryFn: async () => {
      const result = await getMaterialAction({ data: props })
      if ('kind' in result) {
        if (result.kind === 'unauthorized') {
          throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
            statusCode: 401,
          })
        }
        throw new RestError(
          'Material indisponível.',
          result.kind === 'not-found' ? 404 : 503,
        )
      }
      return result
    },
    retry: false,
    refetchOnWindowFocus: false,
  })

  useEffect(() => {
    if (query.error instanceof AuthError) void navigateTo('login')
  }, [query.error, navigateTo])

  return {
    detail: query.data ?? null,
    isLoading: query.isPending,
    isPrivateAbsence: query.error instanceof RestError && query.error.statusCode === 404,
    isRecoverableError: Boolean(query.error) && !(query.error instanceof AuthError),
    handleRetry: query.refetch,
  }
}
