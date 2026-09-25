import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import {
  MATERIAL_DETAIL_ID_PATTERN,
  type MaterialDetail,
} from '@/core/learning/material-detail'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type MaterialPageProps = {
  goalId: string
  skillId: string
  competencyId: string
  materialId: string
}

export type GetMaterialDetailActionFailure =
  | { kind: 'invalid-request' }
  | { kind: 'unauthorized' }
  | { kind: 'not-found' }
  | { kind: 'unavailable'; statusCode?: number }

export type GetMaterialDetailActionResult =
  | MaterialDetail
  | GetMaterialDetailActionFailure

type ValidatedActionInput = MaterialPageProps | { kind: 'invalid-request' }

export const getMaterialDetailAction = createServerFn({ method: 'GET' })
  .validator((input: unknown): ValidatedActionInput => {
    if (!isRecord(input)) return { kind: 'invalid-request' }

    if (
      !isIdentifier(input.goalId) ||
      !isIdentifier(input.skillId) ||
      !isIdentifier(input.competencyId) ||
      !isIdentifier(input.materialId)
    ) {
      return { kind: 'invalid-request' }
    }

    return {
      goalId: input.goalId,
      skillId: input.skillId,
      competencyId: input.competencyId,
      materialId: input.materialId,
    }
  })
  .handler(async ({ data }): Promise<GetMaterialDetailActionResult> => {
    if ('kind' in data) return data

    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const learningService = LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      )

      return await learningService.getMaterialDetail(access.accessToken, data)
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

export function useMaterialPage({
  competencyId,
  goalId,
  materialId,
  skillId,
}: MaterialPageProps) {
  const { navigateTo, navigateToActivity } = useNavigation()
  const [hasActivityFailure, setHasActivityFailure] = useState(false)
  const [isOpeningActivity, setIsOpeningActivity] = useState(false)
  const query = useQuery({
    queryKey: ['learning', 'material-detail', goalId, skillId, competencyId, materialId],
    queryFn: async () => {
      const result = await getMaterialDetailAction({
        data: { goalId, skillId, competencyId, materialId },
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

  async function handleOpenRecommendation(activityId: string) {
    if (isOpeningActivity) return

    setHasActivityFailure(false)
    setIsOpeningActivity(true)

    try {
      await navigateToActivity(goalId, skillId, competencyId, activityId)
    } catch {
      setHasActivityFailure(true)
    } finally {
      setIsOpeningActivity(false)
    }
  }

  async function handleRetry() {
    await query.refetch()
  }

  return {
    detail: query.data ?? null,
    error: query.error ?? null,
    hasActivityFailure,
    handleOpenRecommendation,
    handleRetry,
    isLoading: query.isPending,
    isOpeningActivity,
    isPrivateAbsence,
    isRecoverableError: Boolean(query.error) && !isPrivateAbsence && !isSessionRejected,
  }
}

export type MaterialPageController = ReturnType<typeof useMaterialPage>

function isFailure(
  result: GetMaterialDetailActionResult,
): result is Exclude<GetMaterialDetailActionResult, MaterialDetail> {
  return 'kind' in result
}

function mapFailure(
  failure: Exclude<GetMaterialDetailActionResult, MaterialDetail>,
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
  return typeof value === 'string' && MATERIAL_DETAIL_ID_PATTERN.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
