import { useMutation, useQueryClient } from '@tanstack/react-query'
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
    content: z.string(),
    expectedVersion: z.number().int().min(1),
  })
  .strict()

export type EditLearnerMemoryResult =
  | { kind: 'ok'; memory: LearnerMemory }
  | { kind: 'conflict' | 'invalid' | 'not-found' }

export const editLearnerMemoryServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }): Promise<EditLearnerMemoryResult> => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    try {
      const memory = await service.editLearnerMemory(accessToken, data.memoryId, {
        content: data.content,
        expectedVersion: data.expectedVersion,
      })
      return { kind: 'ok', memory }
    } catch (error) {
      if (error instanceof RestError) {
        if (error.statusCode === HTTP_STATUS_CODE.conflict) return { kind: 'conflict' }
        if (error.statusCode === HTTP_STATUS_CODE.unprocessableEntity)
          return { kind: 'invalid' }
        if (error.statusCode === HTTP_STATUS_CODE.notFound) return { kind: 'not-found' }
      }
      throw error
    }
  })

export const useEditLearnerMemoryAction = (accountEmail: string) => {
  const queryClient = useQueryClient()
  const { isPending, mutateAsync } = useMutation({
    mutationFn: (input: { memoryId: string; content: string; expectedVersion: number }) =>
      editLearnerMemoryServer({ data: { accountEmail, ...input } }),
    onSuccess: async (result) => {
      if (result.kind === 'invalid') return
      // A conflict or a missing memory also refreshes the cache so the page reads
      // the current server state before it reports the outcome.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['learner-memories'] }),
        queryClient.invalidateQueries({ queryKey: ['learner-memory'] }),
      ])
    },
  })

  return { isEditingLearnerMemory: isPending, editLearnerMemory: mutateAsync }
}
