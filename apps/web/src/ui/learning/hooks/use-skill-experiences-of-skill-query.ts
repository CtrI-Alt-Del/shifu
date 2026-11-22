import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'

export const SKILL_EXPERIENCES_OF_SKILL_QUERY_KEY = [
  'learning',
  'skill-experiences-of-skill',
] as const

const listSkillExperiencesOfSkill = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: { skillId: string }) => data)
  .handler(
    async ({
      data,
      context,
    }: {
      data: { skillId: string }
      context: RequestTelemetryContext
    }): Promise<SkillExperienceReference[]> => {
      const access = await getBetterAuthProvider().getCurrentAccess(
        getRequest(),
        context.requestId,
      )
      if (!access) {
        throw new AppError(
          'Sua sessão expirou. Atualize a página.',
          'Erro de autenticação',
        )
      }

      const learningService = LearningService(
        createServerRequestClient(context, { baseUrl: SERVER_ENV.shifuServerAppUrl }),
      )
      return learningService.listSkillExperiencesOfSkill(access.accessToken, data.skillId)
    },
  )

export const useSkillExperiencesOfSkillQuery = (skillId: string | null) => {
  const {
    data: skillExperiencesOfSkill = [],
    error: skillExperiencesOfSkillError,
    isLoading: isLoadingSkillExperiencesOfSkill,
  } = useQuery({
    queryKey: [...SKILL_EXPERIENCES_OF_SKILL_QUERY_KEY, skillId],
    queryFn: () => listSkillExperiencesOfSkill({ data: { skillId: skillId as string } }),
    enabled: skillId !== null,
    retry: false,
  })

  return {
    skillExperiencesOfSkill,
    skillExperiencesOfSkillError,
    isLoadingSkillExperiencesOfSkill,
  }
}
