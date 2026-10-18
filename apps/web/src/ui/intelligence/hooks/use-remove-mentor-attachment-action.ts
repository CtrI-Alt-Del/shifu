import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { useMutation } from '@tanstack/react-query'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z
  .object({
    accountEmail: z.string().email(),
    batchId: ID,
    attachmentId: ID,
  })
  .strict()

export const removeMentorAttachmentServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    return service.removeMentorAttachment(accessToken, data.batchId, data.attachmentId)
  })

type RemoveMentorAttachmentInput = {
  accountEmail: string
  batchId: string
  attachmentId: string
}

export const useRemoveMentorAttachmentAction = () => {
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: ({ accountEmail, batchId, attachmentId }: RemoveMentorAttachmentInput) =>
      removeMentorAttachmentServer({ data: { accountEmail, batchId, attachmentId } }),
  })

  return {
    removeMentorAttachment: mutateAsync,
    removeMentorAttachmentError: error,
    isRemovingMentorAttachment: isPending,
  }
}
