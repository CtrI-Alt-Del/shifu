import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import {
  COMPETENCY_DETAIL_ID_PATTERN,
  type CompetencyDetail,
} from '@/core/learning/competency-detail'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type CompetencyDetailPageProps = {
  goalId: string
  skillId: string
  competencyId: string
}

export type GetCompetencyDetailActionFailure =
  | { kind: 'invalid-request' }
  | { kind: 'unauthorized' }
  | { kind: 'not-found' }
  | { kind: 'unavailable'; statusCode?: number }

export type GetCompetencyDetailActionResult =
  | CompetencyDetail
  | GetCompetencyDetailActionFailure

type ValidatedActionInput = CompetencyDetailPageProps | { kind: 'invalid-request' }

export const getCompetencyDetailAction = createServerFn({ method: 'GET' })
  .validator((input: unknown): ValidatedActionInput => {
    if (!isRecord(input)) return { kind: 'invalid-request' }

    if (
      !isIdentifier(input.goalId) ||
      !isIdentifier(input.skillId) ||
      !isIdentifier(input.competencyId)
    ) {
      return { kind: 'invalid-request' }
    }

    return {
      goalId: input.goalId,
      skillId: input.skillId,
      competencyId: input.competencyId,
    }
  })
  .handler(async ({ data }): Promise<GetCompetencyDetailActionResult> => {
    if ('kind' in data) return data

    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const learningService = LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      )

      return await learningService.getCompetencyDetail(
        access.accessToken,
        data.goalId,
        data.skillId,
        data.competencyId,
      )
    } catch (error) {
      if (error instanceof AuthError && error.kind === 'unavailable') {
        return { kind: 'unavailable', statusCode: error.statusCode }
      }

      if (error instanceof RestError) {
        if (error.statusCode === 401) return { kind: 'unauthorized' }
        if (error.statusCode === 404) return { kind: 'not-found' }
        if (error.statusCode === 429) {
          return { kind: 'unavailable', statusCode: error.statusCode }
        }
      }

      return { kind: 'unavailable' }
    }
  })

export function useCompetencyDetailPage({
  competencyId,
  goalId,
  skillId,
}: CompetencyDetailPageProps) {
  const { navigateTo } = useNavigation()
  const query = useQuery({
    queryKey: ['learning', 'competency-detail', goalId, skillId, competencyId],
    queryFn: async () => {
      const result = await getCompetencyDetailAction({
        data: { goalId, skillId, competencyId },
      })

      if (isFailure(result)) mapFailure(result)

      return result
    },
    refetchOnWindowFocus: false,
    retry: (failureCount, error) =>
      error instanceof RestError && error.statusCode === 429 && failureCount < 2,
    retryDelay: (_failureCount, error) => (error instanceof RestError ? 1000 : 0),
  })

  const isPrivateAbsence =
    query.error instanceof RestError && query.error.statusCode === 404
  const isSessionRejected = query.error instanceof AuthError

  useEffect(() => {
    if (!isSessionRejected) return

    void navigateTo('login')
  }, [isSessionRejected, navigateTo])

  return {
    detail: query.data ?? null,
    error: query.error ?? null,
    handleRetry: query.refetch,
    isLoading: query.isPending,
    isPrivateAbsence,
    isRecoverableError: Boolean(query.error) && !isPrivateAbsence && !isSessionRejected,
  }
}

export type CompetencyDetailPageController = ReturnType<typeof useCompetencyDetailPage>

function isFailure(
  result: GetCompetencyDetailActionResult,
): result is Exclude<GetCompetencyDetailActionResult, CompetencyDetail> {
  return 'kind' in result
}

function mapFailure(
  failure: Exclude<GetCompetencyDetailActionResult, CompetencyDetail>,
): never {
  if (failure.kind === 'unauthorized') {
    throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
      statusCode: 401,
    })
  }

  if (failure.kind === 'not-found') {
    throw new RestError('Recurso não encontrado.', 404)
  }

  if (failure.kind === 'invalid-request') {
    throw new RestError('A solicitação de aprendizagem é inválida.', 422)
  }

  throw new RestError('Serviço temporariamente indisponível.', failure.statusCode ?? 503)
}

function isIdentifier(value: unknown): value is string {
  return typeof value === 'string' && COMPETENCY_DETAIL_ID_PATTERN.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
