import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { z } from 'zod'

import type { StreakReminderPreference } from '@/core/communication/streak-reminder-preference'
import { RestError } from '@/core/errors/rest-error'
import type { ServerFunctionFailure } from '@/core/shared/responses/server-function-failure'
import { runStreakReminderRequest } from '@/provision/push/streak-reminder-server-provider'
import { STREAK_REMINDER_PREFERENCE_QUERY_KEY } from '@/ui/gamification/constants/streak-reminder-query-keys'

const ACCOUNT_EMAIL = z.string().email()

const CHANGE_STREAK_REMINDER_PREFERENCE_INPUT = z
  .object({ accountEmail: ACCOUNT_EMAIL, enabled: z.boolean() })
  .strict()

const FAILURE_MESSAGE = 'Não foi possível concluir agora. Tente novamente.'

export type ChangeStreakReminderPreferenceResult =
  | { kind: 'ok'; preference: StreakReminderPreference }
  | ServerFunctionFailure

export const changeStreakReminderPreference = createServerFn({ method: 'POST' })
  .validator((data: unknown) => CHANGE_STREAK_REMINDER_PREFERENCE_INPUT.parse(data))
  .handler(async ({ data }): Promise<ChangeStreakReminderPreferenceResult> => {
    const result = await runStreakReminderRequest(
      data.accountEmail,
      ({ accessToken, communicationService }) =>
        communicationService.changeStreakReminderPreference(accessToken, data.enabled),
    )
    if (result.kind === 'ok') return { kind: 'ok', preference: result.value }
    return result
  })

export const useChangeStreakReminderPreferenceAction = (accountEmail: string) => {
  const queryClient = useQueryClient()
  const { mutateAsync, isPending, error } = useMutation({
    mutationFn: async (enabled: boolean) => {
      const result = await changeStreakReminderPreference({
        data: { accountEmail, enabled },
      })
      if (result.kind === 'ok') return result.preference
      throw new RestError(FAILURE_MESSAGE, result.statusCode)
    },
    onSuccess: (preference) => {
      queryClient.setQueryData(STREAK_REMINDER_PREFERENCE_QUERY_KEY, preference)
    },
  })

  return {
    changeStreakReminderPreferenceError: error,
    isChangingStreakReminderPreference: isPending,
    changeStreakReminderPreference: mutateAsync,
  }
}
