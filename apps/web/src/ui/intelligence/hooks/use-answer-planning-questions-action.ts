import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import {
  PLANNING_ID_PATTERN,
  PLANNING_OTHER_TEXT_MAX_LENGTH,
  type PlanningAnswersSubmission,
} from '@/core/intelligence/planning-session'
import { withPlanningService } from '@/provision/planning/planning-server-provider'

import { unwrapPlanningResult } from './planning-request-error'

const IDENTIFIER = z.string().min(1).max(64)
const INPUT = z
  .object({
    planningId: z.string().regex(PLANNING_ID_PATTERN),
    batchId: IDENTIFIER,
    answers: z
      .array(
        z
          .object({
            questionId: IDENTIFIER,
            optionIds: z.array(IDENTIFIER).max(8),
            otherText: z
              .string()
              .trim()
              .min(1)
              .max(PLANNING_OTHER_TEXT_MAX_LENGTH)
              .optional(),
          })
          .strict(),
      )
      .min(1)
      .max(8),
  })
  .strict()

export const answerPlanningQuestionsServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(({ data }) =>
    withPlanningService(getRequest(), (service, accessToken) =>
      service.answerPlanningQuestions(accessToken, data.planningId, {
        batchId: data.batchId,
        answers: data.answers,
      }),
    ),
  )

export const useAnswerPlanningQuestionsAction = (planningId: string) => {
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async (submission: PlanningAnswersSubmission) =>
      unwrapPlanningResult(
        await answerPlanningQuestionsServer({ data: { planningId, ...submission } }),
      ),
  })

  return {
    answerPlanningQuestions: mutateAsync,
    answerPlanningQuestionsError: error,
    isAnsweringPlanningQuestions: isPending,
  }
}
