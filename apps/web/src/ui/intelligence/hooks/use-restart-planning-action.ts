import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import {
  PLANNING_ID_PATTERN,
  PLANNING_INTENT_MAX_LENGTH,
} from '@/core/intelligence/planning-session'
import { withPlanningService } from '@/provision/planning/planning-server-provider'

import {
  isPlanningQuotaExhaustedError,
  unwrapPlanningResult,
} from './planning-request-error'
import { AI_QUOTA_USAGE_QUERY_KEY } from './ai-quota-usage-query-key'

const INPUT = z
  .object({
    planningId: z.string().regex(PLANNING_ID_PATTERN),
    initialIntent: z.string().trim().min(1).max(PLANNING_INTENT_MAX_LENGTH),
  })
  .strict()

export const restartPlanningServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(({ data }) =>
    withPlanningService(getRequest(), (service, accessToken) =>
      service.restartPlanning(accessToken, data.planningId, data.initialIntent),
    ),
  )

export const useRestartPlanningAction = (planningId: string) => {
  const queryClient = useQueryClient()
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async (initialIntent: string) =>
      unwrapPlanningResult(
        await restartPlanningServer({ data: { planningId, initialIntent } }),
      ),
    onError: (error) => {
      if (isPlanningQuotaExhaustedError(error))
        void queryClient.invalidateQueries({ queryKey: AI_QUOTA_USAGE_QUERY_KEY })
    },
  })

  return {
    restartPlanning: mutateAsync,
    restartPlanningError: error,
    isRestartingPlanning: isPending,
  }
}
