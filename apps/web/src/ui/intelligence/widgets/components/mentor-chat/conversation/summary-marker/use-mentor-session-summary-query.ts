import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { useQuery } from '@tanstack/react-query'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const INPUT = z
  .object({
    sessionId: z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/),
  })
  .strict()

export const getMentorSessionSummaryServer = createServerFn({ method: 'GET' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { accessToken, service } = await getMentorScopedService(getRequest())
    return service.getMentorSessionSummary(accessToken, data.sessionId)
  })

type MentorSessionSummaryQueryInput = {
  sessionId: string | null
  version: number | null
  isEnabled: boolean
}

export const useMentorSessionSummaryQuery = ({
  sessionId,
  version,
  isEnabled,
}: MentorSessionSummaryQueryInput) => {
  const {
    data,
    error,
    isLoading: isLoadingSummary,
    refetch,
  } = useQuery({
    queryKey: ['mentor-session-summary', sessionId, version],
    queryFn: () =>
      getMentorSessionSummaryServer({ data: { sessionId: sessionId as string } }),
    enabled: Boolean(sessionId && version !== null && isEnabled),
    retry: false,
    gcTime: 0,
    staleTime: Number.POSITIVE_INFINITY,
  })

  return {
    summaryContent: data ?? null,
    summaryError: error,
    isLoadingSummary,
    refetchSummary: refetch,
  }
}
