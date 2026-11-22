import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { z } from 'zod'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'
import { serverFunctionTelemetryMiddleware } from '@/start'

export const OTHER_SKILL_EXPERIENCES_QUERY_KEY = [
  'intelligence',
  'other-skill-experiences',
] as const

const INPUT = z.object({ skillId: z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/) }).strict()

export const listOtherSkillExperiencesServer = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: unknown) => INPUT.parse(data))
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

export function useOtherSkillExperiencesQuery(skillId: string | null) {
  const {
    data,
    error,
    isLoading: isLoadingOtherSkillExperiences,
  } = useQuery({
    queryKey: [...OTHER_SKILL_EXPERIENCES_QUERY_KEY, skillId],
    queryFn: () =>
      listOtherSkillExperiencesServer({ data: { skillId: skillId as string } }),
    enabled: skillId !== null,
    retry: false,
  })

  // The warning is optional: a failed lookup behaves like an empty one.
  const otherSkillExperiences = error ? [] : (data ?? [])

  return { otherSkillExperiences, isLoadingOtherSkillExperiences }
}
