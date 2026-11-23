import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { SkillEvolution } from '@/core/learning/skill-evolution'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'

type SkillEvolutionInput = { skillExperienceId: string }

type SkillEvolutionResult =
  | { kind: 'success'; evolution: SkillEvolution }
  | { kind: 'unauthorized' | 'forbidden' | 'unavailable'; statusCode?: number }

export const getSkillEvolution = createServerFn({ method: 'GET' })
  .validator((data: SkillEvolutionInput) => data)
  .handler(
    async ({ data }: { data: SkillEvolutionInput }): Promise<SkillEvolutionResult> => {
      try {
        const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
        if (!access) return { kind: 'unauthorized' }

        const learningService = LearningService(createServerRequestClient(undefined))
        const evolution = await learningService.getSkillEvolution(
          access.accessToken,
          data.skillExperienceId,
        )
        return { kind: 'success', evolution }
      } catch (error) {
        if (error instanceof AuthError) {
          return error.kind === 'authentication-rejected'
            ? { kind: 'unauthorized', statusCode: error.statusCode }
            : { kind: 'unavailable', statusCode: error.statusCode }
        }

        if (error instanceof RestError) {
          if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
            return { kind: 'unauthorized' }
          if (error.statusCode === HTTP_STATUS_CODE.forbidden)
            return { kind: 'forbidden' }
          return { kind: 'unavailable', statusCode: error.statusCode }
        }

        return { kind: 'unavailable' }
      }
    },
  )

export function useSkillEvolutionQuery(skillExperienceId: string | null) {
  const {
    data: skillEvolution = null,
    error: skillEvolutionError,
    isPending: isPendingSkillEvolution,
    isFetching: isFetchingSkillEvolution,
    refetch: refetchSkillEvolution,
  } = useQuery({
    queryKey: ['learning', 'panorama', 'skill-evolution', skillExperienceId],
    enabled: skillExperienceId !== null,
    retry: false,
    queryFn: async () => {
      const result = await getSkillEvolution({
        data: { skillExperienceId: skillExperienceId as string },
      })

      if (result.kind === 'success') return result.evolution
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
    skillEvolution,
    skillEvolutionError,
    isLoadingSkillEvolution: isPendingSkillEvolution && skillExperienceId !== null,
    isFetchingSkillEvolution,
    refetchSkillEvolution,
  }
}
