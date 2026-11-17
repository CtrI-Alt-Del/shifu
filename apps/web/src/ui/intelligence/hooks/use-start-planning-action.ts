import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { withPlanningService } from '@/provision/planning/planning-server-provider'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'

import {
  isPlanningQuotaExhaustedError,
  unwrapPlanningResult,
} from './planning-request-error'
import { AI_QUOTA_USAGE_QUERY_KEY } from './ai-quota-usage-query-key'

const startPlanningSession = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: { initialIntent: string }) => data)
  .handler(
    ({
      data,
      context,
    }: {
      data: { initialIntent: string }
      context: RequestTelemetryContext
    }) =>
      withPlanningService(
        getRequest(),
        (service, accessToken) => service.startPlanning(accessToken, data.initialIntent),
        context,
      ),
  )

export type PlanningSession = {
  createdAt: string
  id: string
}

export const useStartPlanningAction = () => {
  const queryClient = useQueryClient()
  const { error, isPending, mutate } = useMutation({
    mutationFn: async (initialIntent: string): Promise<PlanningSession> => {
      const session = unwrapPlanningResult(
        await startPlanningSession({ data: { initialIntent } }),
      )
      return { createdAt: session.created_at, id: session.id }
    },
    onError: (error) => {
      if (isPlanningQuotaExhaustedError(error))
        void queryClient.invalidateQueries({ queryKey: AI_QUOTA_USAGE_QUERY_KEY })
    },
  })

  return {
    error,
    isPending,
    startPlanning: mutate,
  }
}
