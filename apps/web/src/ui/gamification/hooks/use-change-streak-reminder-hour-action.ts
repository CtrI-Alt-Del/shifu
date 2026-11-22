import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { z } from 'zod'

import type { StreakReminder } from '@/core/gamification/streak-reminder'
import { RestError } from '@/core/errors/rest-error'
import type { ServerFunctionFailure } from '@/core/shared/responses/server-function-failure'
import { runStreakReminderRequest } from '@/provision/push/streak-reminder-server-provider'
import { STREAK_REMINDER_QUERY_KEY } from '@/ui/gamification/constants/streak-reminder-query-keys'

const ACCOUNT_EMAIL = z.string().email()

const CHANGE_STREAK_REMINDER_HOUR_INPUT = z
  .object({ accountEmail: ACCOUNT_EMAIL, hour: z.number().int().min(6).max(22) })
  .strict()

const FAILURE_MESSAGE = 'Não foi possível concluir agora. Tente novamente.'

export type ChangeStreakReminderHourResult =
  | { kind: 'ok'; streakReminder: StreakReminder }
  | ServerFunctionFailure

export const changeStreakReminderHour = createServerFn({ method: 'POST' })
  .validator((data: unknown) => CHANGE_STREAK_REMINDER_HOUR_INPUT.parse(data))
  .handler(async ({ data }): Promise<ChangeStreakReminderHourResult> => {
    const result = await runStreakReminderRequest(
      data.accountEmail,
      ({ accessToken, gamificationService }) =>
        gamificationService.changeStreakReminderHour(accessToken, data.hour),
    )
    if (result.kind === 'ok') return { kind: 'ok', streakReminder: result.value }
    return result
  })

export const useChangeStreakReminderHourAction = (accountEmail: string) => {
  const queryClient = useQueryClient()
  const { mutateAsync, isPending, error } = useMutation({
    mutationFn: async (hour: number) => {
      const result = await changeStreakReminderHour({ data: { accountEmail, hour } })
      if (result.kind === 'ok') return result.streakReminder
      throw new RestError(FAILURE_MESSAGE, result.statusCode)
    },
    onSuccess: (streakReminder) => {
      queryClient.setQueryData(STREAK_REMINDER_QUERY_KEY, streakReminder)
    },
  })

  return {
    changeStreakReminderHourError: error,
    isChangingStreakReminderHour: isPending,
    changeStreakReminderHour: mutateAsync,
  }
}
