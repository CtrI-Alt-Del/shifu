import { useMutation } from '@tanstack/react-query'

import { removeMentorSessionServer } from './mentor-server-functions'

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
