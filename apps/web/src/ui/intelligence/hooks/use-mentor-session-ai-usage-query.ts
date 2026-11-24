import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'
import { useQuery } from '@tanstack/react-query'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

import { AI_QUOTA_USAGE_QUERY_KEY } from './ai-quota-usage-query-key'

const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z
  .object({
    accountEmail: z.string().email(),
    sessionId: ID,
  })
  .strict()

export const getMentorSessionAiUsageServer = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data, context }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
      context,
    )
    return service.getMentorSessionAiUsage(accessToken, data.sessionId)
  })

export const useMentorSessionAiUsageQuery = (
  accountEmail: string,
  sessionId: string | null,
) => {
  // The key starts with the quota key, so every quota refresh after an answer also
  // reloads the usage of each answer.
  const { data: mentorSessionAiUsage = [] } = useQuery({
    queryKey: [...AI_QUOTA_USAGE_QUERY_KEY, 'mentor-session', accountEmail, sessionId],
    queryFn: () =>
      getMentorSessionAiUsageServer({
        data: { accountEmail, sessionId: sessionId as string },
      }),
    enabled: Boolean(sessionId),
    retry: false,
  })

  return { mentorSessionAiUsage }
}
