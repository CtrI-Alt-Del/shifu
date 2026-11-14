import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { serverFunctionTelemetryMiddleware } from '@/start'
import { getRequest } from '@tanstack/react-start/server'
import { useQuery } from '@tanstack/react-query'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z
  .object({
    accountEmail: z.string().email(),
    batchId: ID,
  })
  .strict()

export const getMentorAttachmentBatchServer = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data, context }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
      context,
    )
    return service.getMentorAttachmentBatch(accessToken, data.batchId)
  })

export const useMentorAttachmentBatchQuery = (
  accountEmail: string,
  batchId: string | null,
  isActive: boolean,
) => {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['mentor-attachment-batch', accountEmail, batchId],
    queryFn: () =>
      getMentorAttachmentBatchServer({
        data: { accountEmail, batchId: batchId as string },
      }),
    enabled: Boolean(batchId && isActive),
    refetchInterval: isActive ? 1_500 : false,
    refetchIntervalInBackground: false,
    retry: false,
    gcTime: 0,
  })

  return {
    mentorAttachmentBatch: data ?? null,
    mentorAttachmentBatchError: error,
    isReadingMentorAttachmentBatch: isPending,
    refreshMentorAttachmentBatch: refetch,
  }
}
