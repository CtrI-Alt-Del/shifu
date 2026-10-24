import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'
import { useMutation } from '@tanstack/react-query'
import type { SubmitMentorMessageInput } from '@/core/intelligence/mentor-response'
import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'
const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const HINT = z
  .object({
    goalId: ID.nullable(),
    skillId: ID.nullable(),
    competencyId: ID.nullable(),
    materialId: ID.nullable(),
    activityId: ID.nullable(),
  })
  .strict()
const INPUT = z
  .object({
    accountEmail: z.string().email(),
    sessionId: ID,
    submissionKey: z.uuid({ version: 'v4' }),
    content: z.string(),
    contextHint: HINT.nullable(),
    attachmentBatchId: ID.optional(),
    attachmentIds: z.array(ID).max(5).optional(),
  })
  .refine(
    (input) => Boolean(input.content.trim()) || Boolean(input.attachmentIds?.length),
  )
  .refine((input) => !input.attachmentIds?.length || Boolean(input.attachmentBatchId))
  .strict()
export const submitMentorMessageServer = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data, context }) => {
    const { service, accessToken } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
      context,
    )
    const { accountEmail, sessionId, ...input } = data
    void accountEmail
    return service.submitMentorMessage(accessToken, sessionId, input)
  })
export const useSubmitMentorMessageAction = (accountEmail: string) => {
  const { mutateAsync, isPending } = useMutation({
    mutationFn: (input: SubmitMentorMessageInput & { sessionId: string }) =>
      submitMentorMessageServer({ data: { ...input, accountEmail } }),
  })
  return { submitMentorMessage: mutateAsync, isPending }
}
