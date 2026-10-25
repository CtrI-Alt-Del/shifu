import { z } from 'zod'
import { useCallback } from 'react'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const INPUT = z
  .object({
    accountEmail: z.string().email(),
    search: z.string().optional(),
    cursor: z.string().optional(),
  })
  .strict()

export const listMentorSessionsServer = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data, context }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
      context,
    )
    return service.listMentorSessions(accessToken, {
      search: data.search,
      cursor: data.cursor,
    })
  })

export const useMentorSessionsQuery = (accountEmail: string) => {
  const readMentorSessions = useCallback(
    (input: { search?: string; cursor?: string }) =>
      listMentorSessionsServer({ data: { accountEmail, ...input } }),
    [accountEmail],
  )

  return { readMentorSessions }
}
