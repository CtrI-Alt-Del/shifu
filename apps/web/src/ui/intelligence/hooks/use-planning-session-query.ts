import { z } from 'zod'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { PLANNING_ID_PATTERN } from '@/core/intelligence/planning-session'
import { withPlanningService } from '@/provision/planning/planning-server-provider'

import { unwrapPlanningResult } from './planning-request-error'

const INPUT = z.object({ planningId: z.string().regex(PLANNING_ID_PATTERN) }).strict()

export const PLANNING_SESSION_POLL_INTERVAL_MS = 2_000

export function planningSessionQueryKey(planningId: string) {
  return ['intelligence', 'planning-session', planningId] as const
}

export const getPlanningSessionServer = createServerFn({ method: 'GET' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(({ data }) =>
    withPlanningService(getRequest(), (service, accessToken) =>
      service.getPlanningSession(accessToken, data.planningId),
    ),
  )

export const usePlanningSessionQuery = (planningId: string, isEnabled = true) => {
  const {
    data: planningSession = null,
    error: planningSessionError,
    isPending: isLoadingPlanningSession,
    refetch: refetchPlanningSession,
  } = useQuery({
    queryKey: planningSessionQueryKey(planningId),
    queryFn: async () =>
      unwrapPlanningResult(await getPlanningSessionServer({ data: { planningId } })),
    enabled: isEnabled,
    retry: false,
    refetchOnWindowFocus: false,
    refetchInterval: (query) =>
      query.state.data?.status === 'processing'
        ? PLANNING_SESSION_POLL_INTERVAL_MS
        : false,
  })

  return {
    planningSession,
    planningSessionError,
    isLoadingPlanningSession,
    refetchPlanningSession,
  }
}
