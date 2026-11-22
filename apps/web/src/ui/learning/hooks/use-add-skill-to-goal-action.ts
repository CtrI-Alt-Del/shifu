import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import type { CreatedSkillExperience } from '@/core/learning/created-skill-experience'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'
import { SKILL_EXPERIENCES_OF_SKILL_QUERY_KEY } from '@/ui/learning/hooks/use-skill-experiences-of-skill-query'

const addSkillToGoal = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator(
    (data: { goalId: string; skillId: string; foundationSkillIds: readonly string[] }) =>
      data,
  )
  .handler(
    async ({
      data,
      context,
    }: {
      data: { goalId: string; skillId: string; foundationSkillIds: readonly string[] }
      context: RequestTelemetryContext
    }) => {
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
      return learningService.addSkillToGoal(
        access.accessToken,
        data.goalId,
        data.skillId,
        data.foundationSkillIds,
      )
    },
  )

export function useAddSkillToGoalAction(goalId: string) {
  const queryClient = useQueryClient()
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (input: {
      skillId: string
      foundationSkillIds: readonly string[]
    }): Promise<CreatedSkillExperience[]> =>
      addSkillToGoal({ data: { goalId, ...input } }),
    onSuccess: (_created, { skillId }) =>
      queryClient.invalidateQueries({
        queryKey: [...SKILL_EXPERIENCES_OF_SKILL_QUERY_KEY, skillId],
      }),
  })

  return {
    addSkillToGoalError: error,
    isAddingSkillToGoal: isPending,
    addSkillToGoal: mutateAsync,
    resetAddSkillToGoal: reset,
  }
}
