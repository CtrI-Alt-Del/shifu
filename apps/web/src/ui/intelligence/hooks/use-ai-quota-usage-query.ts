import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import type { AiQuotaUsageReading } from '@/core/intelligence/ai-quota-usage'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { IntelligenceService } from '@/rest/services/intelligence-service'
import { serverFunctionTelemetryMiddleware } from '@/start'

import { AI_QUOTA_USAGE_QUERY_KEY } from './ai-quota-usage-query-key'

export { AI_QUOTA_USAGE_QUERY_KEY }

export const getAiQuotaUsageServer = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .handler(
    async ({
      context,
    }: {
      context: RequestTelemetryContext
    }): Promise<AiQuotaUsageReading> => {
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
      const usage = await intelligenceService.getAiQuotaUsage(access.accessToken)
      // The account id only keys the local warning dismissal; it never leaves the session.
      return { usage, accountId: access.accountId }
    },
  )

export function useAiQuotaUsageQuery() {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: AI_QUOTA_USAGE_QUERY_KEY,
    queryFn: getAiQuotaUsageServer,
    retry: false,
    staleTime: 0,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  })

  async function refetchAiQuotaUsage() {
    await refetch()
  }

  return {
    // A failed reading is unavailable, so a stale value never keeps a block or warning.
    aiQuotaUsage: error ? null : (data?.usage ?? null),
    aiQuotaAccountId: error ? null : (data?.accountId ?? null),
    isLoadingAiQuotaUsage: isPending,
    aiQuotaUsageError: error,
    refetchAiQuotaUsage,
  }
}
