import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'
import { useMutation } from '@tanstack/react-query'
import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'
const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z
  .object({
    accountEmail: z.string().email(),
    sessionId: ID,
    attemptId: ID,
    submissionKey: z.uuid({ version: 'v4' }),
  })
  .strict()
export const retryMentorResponseServer = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data, context }) => {
    const { service, accessToken } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
      context,
    )
    return service.retryMentorResponse(
      accessToken,
      data.sessionId,
      data.attemptId,
      data.submissionKey,
    )
  })
export const useRetryMentorResponseAction = (accountEmail: string) => {
  const { mutateAsync, isPending } = useMutation({
    mutationFn: (input: {
      sessionId: string
      attemptId: string
      submissionKey: string
    }) => retryMentorResponseServer({ data: { ...input, accountEmail } }),
  })
  return { retryMentorResponse: mutateAsync, isPending }
}
