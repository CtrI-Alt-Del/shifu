import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
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
    content: z.string().refine((value) => Boolean(value.trim())),
    contextHint: HINT.nullable(),
  })
  .strict()
export const submitMentorMessageServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { service, accessToken } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    return service.submitMentorMessage(accessToken, data.sessionId, data)
  })
export const useSubmitMentorMessageAction = (accountEmail: string) => {
  const { mutateAsync, isPending } = useMutation({
    mutationFn: (input: SubmitMentorMessageInput & { sessionId: string }) =>
      submitMentorMessageServer({ data: { ...input, accountEmail } }),
  })
  return { submitMentorMessage: mutateAsync, isPending }
}
