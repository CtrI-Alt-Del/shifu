import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { z } from 'zod'

import type { StreakReminder } from '@/core/gamification/streak-reminder'
import { RestError } from '@/core/errors/rest-error'
import type { ServerFunctionFailure } from '@/core/shared/responses/server-function-failure'
import { runStreakReminderRequest } from '@/provision/push/streak-reminder-server-provider'
import { STREAK_REMINDER_QUERY_KEY } from '@/ui/gamification/constants/streak-reminder-query-keys'

const ACCOUNT_EMAIL = z.string().email()

const ANSWER_STREAK_REMINDER_INVITE_INPUT = z
  .object({ accountEmail: ACCOUNT_EMAIL })
  .strict()

const FAILURE_MESSAGE = 'Não foi possível concluir agora. Tente novamente.'

export type AnswerStreakReminderInviteResult =
  | { kind: 'ok'; streakReminder: StreakReminder }
  | ServerFunctionFailure

export const answerStreakReminderInvite = createServerFn({ method: 'POST' })
  .validator((data: unknown) => ANSWER_STREAK_REMINDER_INVITE_INPUT.parse(data))
  .handler(async ({ data }): Promise<AnswerStreakReminderInviteResult> => {
    const result = await runStreakReminderRequest(
      data.accountEmail,
      ({ accessToken, gamificationService }) =>
        gamificationService.answerStreakReminderInvite(accessToken),
    )
    if (result.kind === 'ok') return { kind: 'ok', streakReminder: result.value }
    return result
  })

export const useAnswerStreakReminderInviteAction = (accountEmail: string) => {
  const queryClient = useQueryClient()
  const { mutateAsync, isPending, error } = useMutation({
    mutationFn: async () => {
      const result = await answerStreakReminderInvite({ data: { accountEmail } })
      if (result.kind === 'ok') return result.streakReminder
      throw new RestError(FAILURE_MESSAGE, result.statusCode)
    },
    onSuccess: (streakReminder) => {
      queryClient.setQueryData(STREAK_REMINDER_QUERY_KEY, streakReminder)
    },
  })

  return {
    answerStreakReminderInviteError: error,
    isAnsweringStreakReminderInvite: isPending,
    answerStreakReminderInvite: mutateAsync,
  }
}
