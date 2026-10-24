import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'

const fetchHomeGoals = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .handler(async ({ context }: { context: RequestTelemetryContext }) => {
    const access = await getBetterAuthProvider().getCurrentAccess(
      getRequest(),
      context.requestId,
    )
    if (!access) {
      throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
    }

    const learningService = LearningService(
      createServerRequestClient(context, { baseUrl: SERVER_ENV.shifuServerAppUrl }),
    )
    return learningService.getGoals(access.accessToken)
  })

export function useHomeGoalsQuery() {
  const {
    data: goals = [],
    error: goalsError,
    isLoading: isLoadingGoals,
    refetch: refetchGoals,
  } = useQuery({
    retry: 1,
    queryFn: fetchHomeGoals,
    queryKey: ['learning', 'home-goals'],
  })

  return { goals, goalsError, isLoadingGoals, refetchGoals }
}
