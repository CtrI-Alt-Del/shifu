import { useMutation } from '@tanstack/react-query'

import { createMentorSessionServer } from './mentor-server-functions'

export const useCreateMentorSessionAction = (accountEmail: string) => {
  const { error, isPending, mutateAsync, reset } = useMutation({
    mutationFn: (input: { submissionKey: string; firstMessage: string }) =>
      createMentorSessionServer({ data: { accountEmail, ...input } }),
  })

  return {
    createMentorSession: mutateAsync,
    createMentorSessionError: error,
    isCreatingMentorSession: isPending,
    resetCreateMentorSession: reset,
  }
}
