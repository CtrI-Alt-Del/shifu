import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { z } from 'zod'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { RestError } from '@/core/errors/rest-error'
import type { LearnerMemory } from '@/core/intelligence/learner-memory'
import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const INPUT = z
  .object({
    accountEmail: z.string().email(),
    memoryId: z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/),
  })
  .strict()

type GetLearnerMemoryResult =
  | { kind: 'ok'; memory: LearnerMemory }
  | { kind: 'not-found' }

export const getLearnerMemoryServer = createServerFn({ method: 'GET' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }): Promise<GetLearnerMemoryResult> => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    try {
      const memory = await service.getLearnerMemory(accessToken, data.memoryId)
      return { kind: 'ok', memory }
    } catch (error) {
      if (error instanceof RestError && error.statusCode === HTTP_STATUS_CODE.notFound)
        return { kind: 'not-found' }
      throw error
    }
  })

export const useLearnerMemoryQuery = (
  accountEmail: string,
  memoryId: string | null,
  isEnabled: boolean,
) => {
  const {
    data: result,
    error: memoryError,
    isPending: isLoadingMemory,
    refetch: refetchMemory,
  } = useQuery({
    queryKey: ['learner-memory', accountEmail, memoryId],
    queryFn: () =>
      getLearnerMemoryServer({ data: { accountEmail, memoryId: memoryId as string } }),
    enabled: isEnabled && memoryId !== null,
    retry: false,
  })

  return {
    fetchedMemory: result?.kind === 'ok' ? result.memory : null,
    isMemoryNotFound: result?.kind === 'not-found',
    isLoadingMemory: isEnabled && memoryId !== null && isLoadingMemory,
    memoryError,
    refetchMemory,
  }
}
