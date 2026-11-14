import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { IntelligenceService } from '@/rest/services/intelligence-service'

const startPlanningSession = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: { initialIntent: string }) => data)
  .handler(
    async ({
      data,
      context,
    }: {
      data: { initialIntent: string }
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

      const intelligenceService = IntelligenceService(
        createServerRequestClient(context, { baseUrl: SERVER_ENV.shifuServerAppUrl }),
      )
      return intelligenceService.startPlanning(access.accessToken, data.initialIntent)
    },
  )

export type PlanningSession = {
  createdAt: string
  id: string
}

export const useStartPlanningAction = () => {
  const { error, isPending, mutate } = useMutation({
    mutationFn: async (initialIntent: string): Promise<PlanningSession> => {
      const session = await startPlanningSession({ data: { initialIntent } })
      return { createdAt: session.created_at, id: session.id }
    },
  })

  return {
    error,
    isPending,
    startPlanning: mutate,
  }
}
