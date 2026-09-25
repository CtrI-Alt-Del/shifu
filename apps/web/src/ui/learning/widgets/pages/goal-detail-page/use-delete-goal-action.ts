import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'

const deleteGoal = createServerFn({ method: 'POST' })
  .validator((data: { goalId: string }) => data)
  .handler(async ({ data }) => {
    const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
    if (!access) {
      throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
    }

    const learningService = LearningService(
      AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
    )
    return learningService.deleteGoal(access.accessToken, data.goalId)
  })

export function useDeleteGoalAction(goalId: string) {
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (): Promise<void> => deleteGoal({ data: { goalId } }),
  })

  return {
    deleteGoalError: error ? (error as Error).message : null,
    isDeletingGoal: isPending,
    deleteGoal: mutateAsync,
    resetDeleteGoal: reset,
  }
}
