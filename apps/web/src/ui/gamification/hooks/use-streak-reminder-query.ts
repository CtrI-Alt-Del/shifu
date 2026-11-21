import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'

import type { StreakReminder } from '@/core/gamification/streak-reminder'
import { RestError } from '@/core/errors/rest-error'
import type { ServerFunctionFailure } from '@/core/shared/responses/server-function-failure'
import { runStreakReminderRequest } from '@/provision/push/streak-reminder-server-provider'
import { STREAK_REMINDER_QUERY_KEY } from '@/ui/gamification/constants/streak-reminder-query-keys'

const FAILURE_MESSAGE = 'Não foi possível concluir agora. Tente novamente.'

export type GetStreakReminderResult =
  | { kind: 'ok'; streakReminder: StreakReminder }
  | ServerFunctionFailure

export const getStreakReminder = createServerFn({ method: 'GET' }).handler(
  async (): Promise<GetStreakReminderResult> => {
    const result = await runStreakReminderRequest(
      null,
      ({ accessToken, gamificationService }) =>
        gamificationService.getStreakReminder(accessToken),
    )
    if (result.kind === 'ok') return { kind: 'ok', streakReminder: result.value }
    return result
  },
)

export const useStreakReminderQuery = () => {
  const {
    data: streakReminder = null,
    error: streakReminderError,
    isPending: isLoadingStreakReminder,
    refetch,
  } = useQuery({
    queryKey: STREAK_REMINDER_QUERY_KEY,
    staleTime: 0,
    retry: false,
    queryFn: async () => {
      const result = await getStreakReminder()
      if (result.kind === 'ok') return result.streakReminder
      throw new RestError(FAILURE_MESSAGE, result.statusCode)
    },
  })

  return {
    streakReminder,
    streakReminderError: streakReminderError ?? null,
    isLoadingStreakReminder,
    refetchStreakReminder: refetch,
  }
}
