import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { z } from 'zod'

import {
  LEARNER_MEMORY_CATEGORIES,
  type LearnerMemory,
  type ListLearnerMemoriesInput,
} from '@/core/intelligence/learner-memory'
import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const INPUT = z
  .object({
    accountEmail: z.string().email(),
    q: z.string().max(100).optional(),
    category: z.enum(LEARNER_MEMORY_CATEGORIES).optional(),
  })
  .strict()

const NO_MEMORIES: LearnerMemory[] = []

export const listLearnerMemoriesServer = createServerFn({ method: 'GET' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    return service.listLearnerMemories(accessToken, {
      q: data.q,
      category: data.category,
    })
  })

// No placeholder data: a new filter shows the loading state instead of the old results.
export const useLearnerMemoriesQuery = (
  accountEmail: string,
  filters: ListLearnerMemoriesInput,
) => {
  const {
    data: memories = NO_MEMORIES,
    error: memoriesError,
    isPending: isLoadingMemories,
    refetch: refetchMemories,
  } = useQuery({
    queryKey: ['learner-memories', accountEmail, filters.q, filters.category],
    queryFn: () =>
      listLearnerMemoriesServer({
        data: { accountEmail, q: filters.q, category: filters.category },
      }),
    retry: false,
  })

  return { memories, memoriesError, isLoadingMemories, refetchMemories }
}
