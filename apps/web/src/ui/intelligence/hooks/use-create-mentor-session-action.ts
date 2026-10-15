import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'

import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'
import type { CreateMentorSessionInput } from '@/rest/services/intelligence-service'
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
    submissionKey: z.uuid({ version: 'v4' }),
    firstMessage: z.string().refine((value) => Boolean(value.trim())),
    contextHint: HINT.nullish(),
    attachmentBatchId: ID.optional(),
    attachmentIds: z.array(ID).max(5).optional(),
  })
  .refine((input) => !input.attachmentIds?.length || Boolean(input.attachmentBatchId))
  .strict()
export const createMentorSessionServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { service, accessToken } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    const { accountEmail, ...input } = data
    void accountEmail
    return service.createMentorSession(accessToken, input)
  })

export const useCreateMentorSessionAction = (accountEmail: string) => {
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (input: CreateMentorSessionInput) =>
      createMentorSessionServer({ data: { accountEmail, ...input } }),
  })

  return {
    createMentorSession: mutateAsync,
    createMentorSessionError: error,
    isCreatingMentorSession: isPending,
    resetCreateMentorSession: reset,
  }
}
