import { z } from 'zod'
import { useCallback } from 'react'

import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'
import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'
const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z
  .object({
    accountEmail: z.string().email(),
    sessionId: ID,
    cursor: z.string().optional(),
  })
  .strict()
export const getMentorSessionServer = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data, context }) => {
    const { service, accessToken } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
      context,
    )
    return service.getMentorSession(accessToken, data.sessionId, data.cursor)
  })

export const useMentorSessionQuery = (accountEmail: string) => {
  const readMentorSession = useCallback(
    (sessionId: string, cursor?: string) =>
      getMentorSessionServer({ data: { accountEmail, sessionId, cursor } }),
    [accountEmail],
  )

  return { readMentorSession }
}
