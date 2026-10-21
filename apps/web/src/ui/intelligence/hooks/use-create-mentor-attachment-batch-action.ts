import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { useMutation } from '@tanstack/react-query'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z
  .object({
    accountEmail: z.string().email(),
    sessionId: ID.optional(),
  })
  .strict()

export const createMentorAttachmentBatchServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    return service.createMentorAttachmentBatch(accessToken, data.sessionId)
  })

export const useCreateMentorAttachmentBatchAction = (accountEmail: string) => {
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (sessionId: string | null) =>
      createMentorAttachmentBatchServer({
        data: { accountEmail, ...(sessionId ? { sessionId } : {}) },
      }),
  })

  return {
    createMentorAttachmentBatch: mutateAsync,
    createMentorAttachmentBatchError: error,
    isCreatingMentorAttachmentBatch: isPending,
    resetCreateMentorAttachmentBatch: reset,
  }
}
