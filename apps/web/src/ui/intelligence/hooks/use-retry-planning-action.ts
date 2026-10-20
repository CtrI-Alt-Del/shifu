import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { PLANNING_ID_PATTERN } from '@/core/intelligence/planning-session'
import { withPlanningService } from '@/provision/planning/planning-server-provider'

import { unwrapPlanningResult } from './planning-request-error'

const INPUT = z.object({ planningId: z.string().regex(PLANNING_ID_PATTERN) }).strict()

export const retryPlanningServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(({ data }) =>
    withPlanningService(getRequest(), (service, accessToken) =>
      service.retryPlanning(accessToken, data.planningId),
    ),
  )

export const useRetryPlanningAction = (planningId: string) => {
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async () =>
      unwrapPlanningResult(await retryPlanningServer({ data: { planningId } })),
  })

  return {
    retryPlanning: mutateAsync,
    retryPlanningError: error,
    isRetryingPlanning: isPending,
  }
}
