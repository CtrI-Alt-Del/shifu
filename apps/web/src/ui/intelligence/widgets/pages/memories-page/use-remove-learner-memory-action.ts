import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { z } from 'zod'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const INPUT = z
  .object({
    accountEmail: z.string().email(),
    memoryId: z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/),
  })
  .strict()

export const removeLearnerMemoryServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    await service.removeLearnerMemory(accessToken, data.memoryId)
    return { kind: 'ok' as const }
  })

export const useRemoveLearnerMemoryAction = (accountEmail: string) => {
  const queryClient = useQueryClient()
  const { isPending, mutateAsync } = useMutation({
    mutationFn: (memoryId: string) =>
      removeLearnerMemoryServer({ data: { accountEmail, memoryId } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['learner-memories'] })
      void queryClient.invalidateQueries({ queryKey: ['learner-memory'] })
    },
  })

  return { isRemovingLearnerMemory: isPending, removeLearnerMemory: mutateAsync }
}
