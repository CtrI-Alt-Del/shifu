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

type RemoveSkillInput = { goalId: string; skillId: string }

const removeSkill = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: RemoveSkillInput) => data)
  .handler(
    async ({
      data,
      context,
    }: {
      data: RemoveSkillInput
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

      await LearningService(
        createServerRequestClient(context, { baseUrl: SERVER_ENV.shifuServerAppUrl }),
      ).removeSkill(access.accessToken, data.goalId, data.skillId)
    },
  )

export function useRemoveSkillAction(ids: RemoveSkillInput) {
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (): Promise<void> => removeSkill({ data: ids }),
  })

  return {
    removeSkillError: error
      ? 'Não foi possível remover a Habilidade. Tente novamente.'
      : null,
    isRemovingSkill: isPending,
    removeSkill: mutateAsync,
    resetRemoveSkill: reset,
  }
}
