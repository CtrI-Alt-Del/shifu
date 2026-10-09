import { useMutation } from '@tanstack/react-query'

import { renameMentorSessionServer } from './mentor-server-functions'

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
