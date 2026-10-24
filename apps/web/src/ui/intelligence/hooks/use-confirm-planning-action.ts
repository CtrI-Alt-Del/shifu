import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import {
  CONFIRMATION_KEY_PATTERN,
  PLANNING_GOAL_DESCRIPTION_MAX_LENGTH,
  PLANNING_GOAL_TITLE_MAX_LENGTH,
  PLANNING_ID_PATTERN,
} from '@/core/intelligence/planning-session'
import { withPlanningService } from '@/provision/planning/planning-server-provider'

import { unwrapPlanningResult } from './planning-request-error'

const INPUT = z
  .object({
    planningId: z.string().regex(PLANNING_ID_PATTERN),
    confirmationKey: z.string().regex(CONFIRMATION_KEY_PATTERN),
    title: z.string().trim().min(1).max(PLANNING_GOAL_TITLE_MAX_LENGTH),
    description: z.string().trim().min(1).max(PLANNING_GOAL_DESCRIPTION_MAX_LENGTH),
  })
  .strict()

export type ConfirmPlanningInput = {
  confirmationKey: string
  title: string
  description: string
}

export const confirmPlanningServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(({ data }) =>
    withPlanningService(getRequest(), (service, accessToken) =>
      service.confirmPlanning(accessToken, data.planningId, {
        confirmationKey: data.confirmationKey,
        title: data.title,
        description: data.description,
      }),
    ),
  )

export const useConfirmPlanningAction = (planningId: string) => {
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async (input: ConfirmPlanningInput) =>
      unwrapPlanningResult(
        await confirmPlanningServer({ data: { planningId, ...input } }),
      ),
  })

  return {
    confirmPlanning: mutateAsync,
    confirmPlanningError: error,
    isConfirmingPlanning: isPending,
  }
}
