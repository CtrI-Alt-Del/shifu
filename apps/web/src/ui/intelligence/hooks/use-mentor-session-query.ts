import { useCallback } from 'react'

import { getMentorSessionServer } from './mentor-server-functions'

export const useMentorSessionQuery = (accountEmail: string) => {
  const readMentorSession = useCallback(
    (sessionId: string, cursor?: string) =>
      getMentorSessionServer({ data: { accountEmail, sessionId, cursor } }),
    [accountEmail],
  )

  return { readMentorSession }
}
