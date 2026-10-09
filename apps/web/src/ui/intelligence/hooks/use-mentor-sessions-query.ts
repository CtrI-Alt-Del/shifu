import { useCallback } from 'react'

import { listMentorSessionsServer } from './mentor-server-functions'

export const useMentorSessionsQuery = (accountEmail: string) => {
  const readMentorSessions = useCallback(
    (input: { search?: string; cursor?: string }) =>
      listMentorSessionsServer({ data: { accountEmail, ...input } }),
    [accountEmail],
  )

  return { readMentorSessions }
}
