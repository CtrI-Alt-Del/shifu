import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { CreatedSkillExperience } from '@/core/learning/skill-catalog'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'

const addSkillToGoal = createServerFn({ method: 'POST' })
  .validator(
    (data: { goalId: string; skillId: string; foundationSkillIds: readonly string[] }) =>
      data,
  )
  .handler(async ({ data }) => {
    const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
    if (!access) {
      throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
    }

    const learningService = LearningService(
      AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
    )
    return learningService.addSkillToGoal(
      access.accessToken,
      data.goalId,
      data.skillId,
      data.foundationSkillIds,
    )
  })

export function useAddSkillToGoalAction(goalId: string) {
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (input: {
      skillId: string
      foundationSkillIds: readonly string[]
    }): Promise<CreatedSkillExperience[]> =>
      addSkillToGoal({ data: { goalId, ...input } }),
  })

  return {
    addSkillToGoalError: error,
    isAddingSkillToGoal: isPending,
    addSkillToGoal: mutateAsync,
    resetAddSkillToGoal: reset,
  }
}
