import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import {
  PLANNING_ID_PATTERN,
  PLANNING_INTENT_MAX_LENGTH,
} from '@/core/intelligence/planning-session'
import { withPlanningService } from '@/provision/planning/planning-server-provider'

import { unwrapPlanningResult } from './planning-request-error'

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
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async (initialIntent: string) =>
      unwrapPlanningResult(
        await restartPlanningServer({ data: { planningId, initialIntent } }),
      ),
  })

  return {
    restartPlanning: mutateAsync,
    restartPlanningError: error,
    isRestartingPlanning: isPending,
  }
}
