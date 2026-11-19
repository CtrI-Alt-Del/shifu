import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'

import type { StreakReminderPreference } from '@/core/communication/streak-reminder-preference'
import { RestError } from '@/core/errors/rest-error'
import type { ServerFunctionFailure } from '@/core/shared/responses/server-function-failure'
import { runStreakReminderRequest } from '@/provision/push/streak-reminder-server-provider'
import { STREAK_REMINDER_PREFERENCE_QUERY_KEY } from '@/ui/gamification/constants/streak-reminder-query-keys'

const FAILURE_MESSAGE = 'Não foi possível concluir agora. Tente novamente.'

export type GetStreakReminderPreferenceResult =
  | { kind: 'ok'; preference: StreakReminderPreference }
  | ServerFunctionFailure

export const getStreakReminderPreference = createServerFn({ method: 'GET' }).handler(
  async (): Promise<GetStreakReminderPreferenceResult> => {
    const result = await runStreakReminderRequest(
      null,
      ({ accessToken, communicationService }) =>
        communicationService.getStreakReminderPreference(accessToken),
    )
    if (result.kind === 'ok') return { kind: 'ok', preference: result.value }
    return result
  },
)

export const useStreakReminderPreferenceQuery = () => {
  const {
    data: preference = null,
    error: preferenceError,
    isPending: isLoadingPreference,
    refetch,
  } = useQuery({
    queryKey: STREAK_REMINDER_PREFERENCE_QUERY_KEY,
    retry: false,
    queryFn: async () => {
      const result = await getStreakReminderPreference()
      if (result.kind === 'ok') return result.preference
      throw new RestError(FAILURE_MESSAGE, result.statusCode)
    },
  })

  return {
    preference,
    preferenceError: preferenceError ?? null,
    isLoadingPreference,
    refetchPreference: refetch,
  }
}
