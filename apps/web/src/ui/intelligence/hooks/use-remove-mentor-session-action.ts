import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { useMutation } from '@tanstack/react-query'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const INPUT = z
  .object({
    accountEmail: z.string().email(),
    sessionId: z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/),
  })
  .strict()

export const removeMentorSessionServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    return service.removeMentorSession(accessToken, data.sessionId)
  })

export const useRemoveMentorSessionAction = (accountEmail: string) => {
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (sessionId: string) =>
      removeMentorSessionServer({ data: { accountEmail, sessionId } }),
  })

  return {
    isRemovingMentorSession: isPending,
    removeMentorSession: mutateAsync,
    removeMentorSessionError: error,
    resetRemoveMentorSession: reset,
  }
}
