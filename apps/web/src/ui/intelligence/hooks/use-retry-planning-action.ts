import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { PLANNING_ID_PATTERN } from '@/core/intelligence/planning-session'
import { withPlanningService } from '@/provision/planning/planning-server-provider'

import {
  isPlanningQuotaExhaustedError,
  unwrapPlanningResult,
} from './planning-request-error'
import { AI_QUOTA_USAGE_QUERY_KEY } from './ai-quota-usage-query-key'

const INPUT = z.object({ planningId: z.string().regex(PLANNING_ID_PATTERN) }).strict()

export const retryPlanningServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(({ data }) =>
    withPlanningService(getRequest(), (service, accessToken) =>
      service.retryPlanning(accessToken, data.planningId),
    ),
  )

export const useRetryPlanningAction = (planningId: string) => {
  const queryClient = useQueryClient()
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async () =>
      unwrapPlanningResult(await retryPlanningServer({ data: { planningId } })),
    onError: (error) => {
      if (isPlanningQuotaExhaustedError(error))
        void queryClient.invalidateQueries({ queryKey: AI_QUOTA_USAGE_QUERY_KEY })
    },
  })

  return {
    retryPlanning: mutateAsync,
    retryPlanningError: error,
    isRetryingPlanning: isPending,
  }
}
