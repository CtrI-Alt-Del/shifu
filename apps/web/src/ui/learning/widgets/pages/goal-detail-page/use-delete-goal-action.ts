import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'

const deleteGoal = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: { goalId: string }) => data)
  .handler(
    async ({
      data,
      context,
    }: {
      data: { goalId: string }
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
      return learningService.deleteGoal(access.accessToken, data.goalId)
    },
  )

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
