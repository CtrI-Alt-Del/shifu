import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { PLANNING_ID_PATTERN } from '@/core/intelligence/planning-session'
import { withPlanningService } from '@/provision/planning/planning-server-provider'

import { unwrapPlanningResult } from './planning-request-error'

const INPUT = z.object({ planningId: z.string().regex(PLANNING_ID_PATTERN) }).strict()

export const cancelPlanningServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(({ data }) =>
    withPlanningService(getRequest(), async (service, accessToken) => {
      await service.cancelPlanning(accessToken, data.planningId)
      return { cancelled: true as const }
    }),
  )

export const useCancelPlanningAction = (planningId: string) => {
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async () =>
      unwrapPlanningResult(await cancelPlanningServer({ data: { planningId } })),
  })

  return {
    cancelPlanning: mutateAsync,
    cancelPlanningError: error,
    isCancellingPlanning: isPending,
  }
}
