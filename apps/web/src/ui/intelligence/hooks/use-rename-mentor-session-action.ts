import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { useMutation } from '@tanstack/react-query'

import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z
  .object({
    accountEmail: z.string().email(),
    sessionId: ID,
    title: z.string(),
  })
  .strict()

export const renameMentorSessionServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }) => {
    const { accessToken, service } = await getMentorScopedService(
      getRequest(),
      data.accountEmail,
    )
    return service.renameMentorSession(accessToken, data.sessionId, data.title)
  })

export const useRenameMentorSessionAction = (accountEmail: string) => {
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (input: { sessionId: string; title: string }) =>
      renameMentorSessionServer({ data: { accountEmail, ...input } }),
  })

  return {
    isRenamingMentorSession: isPending,
    renameMentorSession: mutateAsync,
    renameMentorSessionError: error,
    resetRenameMentorSession: reset,
  }
}
