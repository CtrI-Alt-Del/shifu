import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import type {
  ChoiceActivityDetail,
  ChoiceAnswer,
  ChoiceQuestion,
  ChoiceSubmission,
  ChoiceSubmissionResult,
} from '@/core/learning/choice-activity'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

export type ChoiceActivityRouteProps = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
  onNavigateToAttempt: (attemptId: string, replace?: boolean) => void
  onUnsentAnswersChange: (hasUnsentAnswers: boolean) => void
  onSessionExpired: () => void
}

type InjectedChoiceActivityProps = {
  activity: ChoiceActivityDetail
  onSubmit: (submission: ChoiceSubmission) => Promise<ChoiceSubmissionResult>
  onUnsentAnswersChange?: (hasUnsentAnswers: boolean) => void
}

export type ChoiceActivityPageProps =
  | ChoiceActivityRouteProps
  | InjectedChoiceActivityProps

type ChoiceActivityRouteIds = Omit<
  ChoiceActivityRouteProps,
  'onNavigateToAttempt' | 'onUnsentAnswersChange' | 'onSessionExpired'
>
type ValidatedInput = ChoiceActivityRouteIds | { kind: 'invalid-request' }
type ActionFailure =
  | { kind: 'invalid-request' }
  | { kind: 'unauthorized' }
  | { kind: 'not-found' }
  | { kind: 'unavailable'; statusCode?: number }

export const getChoiceActivityAction = createServerFn({ method: 'GET' })
  .validator((input: unknown): ValidatedInput => {
    if (!isRecord(input)) return { kind: 'invalid-request' }
    if (
      !isIdentifier(input.goalId) ||
      !isIdentifier(input.skillId) ||
      !isIdentifier(input.competencyId) ||
      !isIdentifier(input.activityId)
    ) {
      return { kind: 'invalid-request' }
    }
    return {
      goalId: input.goalId,
      skillId: input.skillId,
      competencyId: input.competencyId,
      activityId: input.activityId,
    }
  })
  .handler(async ({ data }): Promise<ChoiceActivityDetail | ActionFailure> => {
    if ('kind' in data) return data
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).getChoiceActivity(access.accessToken, data)
    } catch (error) {
      if (error instanceof AuthError && error.kind === 'unavailable') {
        return { kind: 'unavailable', statusCode: error.statusCode }
      }
      if (error instanceof RestError) {
        if (error.statusCode === 401) return { kind: 'unauthorized' }
        if (error.statusCode === 404) return { kind: 'not-found' }
        if (error.statusCode === 429) {
          return { kind: 'unavailable', statusCode: error.statusCode }
        }
      }
      return { kind: 'unavailable' }
    }
  })

export const submitChoiceActivityAction = createServerFn({ method: 'POST' })
  .validator(
    (
      input: unknown,
    ):
      | { ids: ChoiceActivityRouteIds; submission: ChoiceSubmission }
      | { kind: 'invalid-request' } => {
      if (!isRecord(input) || !isSubmissionInput(input)) {
        return { kind: 'invalid-request' as const }
      }
      return { ids: input, submission: input.submission }
    },
  )
  .handler(async ({ data }): Promise<ChoiceSubmissionResult | ActionFailure> => {
    if ('kind' in data) return data
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).submitChoiceActivity(access.accessToken, data.ids, data.submission)
    } catch (error) {
      return actionFailure(error)
    }
  })

export function useChoiceActivityPage(props: ChoiceActivityPageProps) {
  const injected = 'activity' in props
  const goalId = injected ? null : props.goalId
  const skillId = injected ? null : props.skillId
  const competencyId = injected ? null : props.competencyId
  const activityId = injected ? null : props.activityId
  const routeIds: ChoiceActivityRouteIds | null = useMemo(
    () =>
      goalId && skillId && competencyId && activityId
        ? { goalId, skillId, competencyId, activityId }
        : null,
    [activityId, competencyId, goalId, skillId],
  )
  const onNavigateToAttempt = injected ? undefined : props.onNavigateToAttempt
  const onSessionExpired = injected ? undefined : props.onSessionExpired
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<readonly ChoiceAnswer[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [hasSubmissionError, setHasSubmissionError] = useState(false)
  const [unsentAnswers, setUnsentAnswers] = useState(false)
  const submissionKeyRef = useRef<string | null>(null)
  const didSubmitRef = useRef(false)
  const activityQuery = useQuery({
    queryKey: [
      'learning',
      'choice-activity',
      ...(routeIds ? Object.values(routeIds) : []),
    ],
    enabled: routeIds !== null,
    queryFn: async () => {
      if (!routeIds) throw new Error('Missing Activity route IDs')
      const result = await getChoiceActivityAction({ data: routeIds })
      if (isActionFailure(result)) throw mapActionFailure(result)
      return result
    },
    retry: false,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    staleTime: 0,
  })
  const activity = injected ? props.activity : (activityQuery.data ?? null)
  const isRouteError = activityQuery.isError && !injected
  const isPrivateAbsence =
    activityQuery.error instanceof RestError && activityQuery.error.statusCode === 404
  const isSessionRejected = activityQuery.error instanceof AuthError

  useEffect(() => {
    if (isSessionRejected) onSessionExpired?.()
  }, [isSessionRejected, onSessionExpired])

  useEffect(() => {
    if (!routeIds || !activity?.unresolvedAttemptId) return
    onNavigateToAttempt?.(activity.unresolvedAttemptId, true)
  }, [activity?.unresolvedAttemptId, onNavigateToAttempt, routeIds])

  const onUnsentAnswersChange =
    !injected && 'onUnsentAnswersChange' in props
      ? props.onUnsentAnswersChange
      : injected
        ? props.onUnsentAnswersChange
        : undefined
  const currentQuestion = activity?.questions[currentQuestionIndex] ?? null
  const selectedOptionKeys = useMemo(
    () =>
      answers.find((answer) => answer.questionKey === currentQuestion?.key)
        ?.selectedOptionKeys ?? [],
    [answers, currentQuestion?.key],
  )
  const hasValidSelection = Boolean(
    activity?.canSubmit &&
      currentQuestion &&
      selectedOptionKeys.length > 0 &&
      selectedOptionKeys.every((optionKey) =>
        currentQuestion.options.some((option) => option.key === optionKey),
      ) &&
      (currentQuestion.kind !== 'single_choice' || selectedOptionKeys.length === 1),
  )
  const isLastQuestion = Boolean(
    activity && currentQuestionIndex === activity.questions.length - 1,
  )
  const hasUnsentAnswers = unsentAnswers && !didSubmitRef.current
  const isSubmissionLocked = submissionKeyRef.current !== null

  useEffect(() => {
    function handleBeforeUnload(event: BeforeUnloadEvent) {
      if (!hasUnsentAnswers) return
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsentAnswers])

  useEffect(() => {
    onUnsentAnswersChange?.(hasUnsentAnswers)
  }, [hasUnsentAnswers, onUnsentAnswersChange])

  function handleToggleOption(optionKey: string) {
    if (
      !activity ||
      !currentQuestion ||
      isSubmitting ||
      isSubmissionLocked ||
      !currentQuestion.options.some((option) => option.key === optionKey)
    )
      return
    setAnswers((currentAnswers) => {
      const currentAnswer = currentAnswers.find(
        (answer) => answer.questionKey === currentQuestion.key,
      )
      const nextOptionKeys =
        currentQuestion.kind === 'single_choice'
          ? [optionKey]
          : currentAnswer?.selectedOptionKeys.includes(optionKey)
            ? currentAnswer.selectedOptionKeys.filter(
                (selectedKey) => selectedKey !== optionKey,
              )
            : [...(currentAnswer?.selectedOptionKeys ?? []), optionKey]
      const nextAnswer = {
        questionKey: currentQuestion.key,
        selectedOptionKeys: nextOptionKeys,
      }
      return currentAnswers.some((answer) => answer.questionKey === currentQuestion.key)
        ? currentAnswers.map((answer) =>
            answer.questionKey === currentQuestion.key ? nextAnswer : answer,
          )
        : [...currentAnswers, nextAnswer]
    })
    setUnsentAnswers(true)
    setHasSubmissionError(false)
  }

  async function handleSubmit() {
    if (!activity || !currentQuestion || !isLastQuestion || !hasValidSelection) return
    const submissionAnswers = activity.questions.map((question) => {
      const answer = answers.find((item) => item.questionKey === question.key)
      return {
        questionKey: question.key,
        selectedOptionKeys:
          question.key === currentQuestion.key
            ? selectedOptionKeys
            : (answer?.selectedOptionKeys ?? []),
      }
    })
    if (submissionAnswers.some((answer) => answer.selectedOptionKeys.length === 0)) return
    if (!submissionKeyRef.current)
      submissionKeyRef.current = globalThis.crypto.randomUUID()
    setIsSubmitting(true)
    setHasSubmissionError(false)
    try {
      const submission = {
        answers: submissionAnswers,
        submissionKey: submissionKeyRef.current,
      }
      const result = injected
        ? await props.onSubmit(submission)
        : await submitChoiceActivityAction({ data: { ...routeIds, submission } })
      if (isActionFailure(result)) throw mapActionFailure(result)
      didSubmitRef.current = true
      setUnsentAnswers(false)
      onUnsentAnswersChange?.(false)
      if (!injected && routeIds) {
        onNavigateToAttempt?.(result.attemptId)
      }
    } catch {
      setHasSubmissionError(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleContinue() {
    if (!activity || !currentQuestion || !hasValidSelection || isSubmitting) return
    if (isLastQuestion) {
      void handleSubmit()
      return
    }
    setCurrentQuestionIndex((index) => Math.min(index + 1, activity.questions.length - 1))
  }

  return {
    activity,
    canContinue: hasValidSelection && !isSubmitting,
    currentQuestion,
    currentQuestionIndex,
    currentQuestionNumber: currentQuestionIndex + 1,
    handleContinue,
    handleRetryLoad: () => activityQuery.refetch(),
    handleToggleOption,
    hasSubmissionError,
    hasUnsentAnswers,
    isLoading: !injected && activityQuery.isPending,
    isPrivateAbsence,
    isRecoverableError: isRouteError && !isPrivateAbsence && !isSessionRejected,
    isSubmissionLocked,
    isLastQuestion,
    isSubmitting,
    selectedOptionKeys,
    totalQuestions: activity?.questions.length ?? 0,
  }
}

export type ChoiceActivityPageController = ReturnType<typeof useChoiceActivityPage>

function isActionFailure(value: unknown): value is ActionFailure {
  return isRecord(value) && typeof value.kind === 'string'
}

function mapActionFailure(failure: ActionFailure): Error {
  if (failure.kind === 'unauthorized')
    return new AuthError('authentication-rejected', 'Sua sessão expirou.', {
      statusCode: 401,
    })
  if (failure.kind === 'not-found') return new RestError('Atividade não encontrada.', 404)
  if (failure.kind === 'invalid-request')
    return new RestError('A solicitação de aprendizagem é inválida.', 422)
  return new RestError('Serviço temporariamente indisponível.', failure.statusCode ?? 503)
}

function actionFailure(error: unknown): ActionFailure {
  if (error instanceof AuthError && error.kind === 'unavailable')
    return { kind: 'unavailable', statusCode: error.statusCode }
  if (error instanceof RestError) {
    if (error.statusCode === 401) return { kind: 'unauthorized' }
    if (error.statusCode === 404) return { kind: 'not-found' }
    if (error.statusCode === 429)
      return { kind: 'unavailable', statusCode: error.statusCode }
  }
  return { kind: 'unavailable' }
}

function isRouteIds(value: Record<string, unknown>): value is Record<string, string> {
  return (
    isIdentifier(value.goalId) &&
    isIdentifier(value.skillId) &&
    isIdentifier(value.competencyId) &&
    isIdentifier(value.activityId)
  )
}

function isSubmissionInput(value: Record<string, unknown>): value is Record<
  string,
  unknown
> & {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
  submission: ChoiceSubmission
} {
  return (
    isRouteIds(value) &&
    isRecord(value.submission) &&
    typeof value.submission.submissionKey === 'string' &&
    Array.isArray(value.submission.answers)
  )
}

function isIdentifier(value: unknown): value is string {
  return typeof value === 'string' && COMPETENCY_DETAIL_ID_PATTERN.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export type ChoiceQuestionProps = {
  question: ChoiceQuestion
  questionNumber: number
  totalQuestions: number
  selectedOptionKeys: readonly string[]
  onToggleOption: (optionKey: string) => void
  disabled?: boolean
}
