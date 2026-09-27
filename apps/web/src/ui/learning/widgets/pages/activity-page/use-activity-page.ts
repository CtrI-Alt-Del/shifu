import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import {
  COMPETENCY_DETAIL_ID_PATTERN,
  type ActivityDifficulty,
} from '@/core/learning/competency-detail'
import type {
  ChoiceActivityDetail,
  ActivityAnswer,
  CodeAnswer,
  PreliminaryQuestionResult,
  ChoiceQuestion,
  ChoiceSubmission,
  ChoiceSubmissionResult,
} from '@/core/learning/choice-activity'
import type { CodePracticeRunner } from '@/core/learning/code-practice-runner'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

export type ActivityRouteProps = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
  onNavigateToAttempt: (attemptId: string, replace?: boolean) => void
  onNavigateToDiagnostic?: () => void
  onUnsentAnswersChange: (hasUnsentAnswers: boolean) => void
  onSessionExpired: () => void
  runnerFactory?: () => CodePracticeRunner
}

type InjectedActivityProps = {
  activity: ChoiceActivityDetail
  onSubmit: (submission: ChoiceSubmission) => Promise<ChoiceSubmissionResult>
  runnerFactory?: () => CodePracticeRunner
  onPreview?: (
    questionKey: string,
    revision: string,
    answer: ActivityAnswer,
  ) => Promise<PreliminaryQuestionResult>
  onUnsentAnswersChange?: (hasUnsentAnswers: boolean) => void
}

export type ActivityPageProps = ActivityRouteProps | InjectedActivityProps

type ActivityRouteIds = Omit<
  ActivityRouteProps,
  | 'onNavigateToAttempt'
  | 'onNavigateToDiagnostic'
  | 'onUnsentAnswersChange'
  | 'onSessionExpired'
>
type ValidatedInput = ActivityRouteIds | { kind: 'invalid-request' }
type ActionFailure =
  | { kind: 'invalid-request' }
  | { kind: 'unauthorized' }
  | { kind: 'not-found' }
  | { kind: 'unavailable'; statusCode?: number }

export const getActivityAction = createServerFn({ method: 'GET' })
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

export const submitActivityAction = createServerFn({ method: 'POST' })
  .validator(
    (
      input: unknown,
    ):
      | { ids: ActivityRouteIds; submission: ChoiceSubmission }
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

export const previewActivityQuestionAction = createServerFn({ method: 'POST' })
  .validator(
    (
      input: unknown,
    ):
      | {
          ids: ActivityRouteIds
          questionKey: string
          activityRevision: string
          answer: ActivityAnswer
        }
      | { kind: 'invalid-request' } => {
      if (
        !isRecord(input) ||
        !isRouteIds(input) ||
        !isQuestionKey(input.questionKey) ||
        typeof input.activityRevision !== 'string' ||
        !input.activityRevision ||
        !isActivityAnswer(input.answer, input.questionKey)
      ) {
        return { kind: 'invalid-request' }
      }
      return {
        ids: {
          goalId: input.goalId,
          skillId: input.skillId,
          competencyId: input.competencyId,
          activityId: input.activityId,
        },
        questionKey: input.questionKey,
        activityRevision: input.activityRevision,
        answer: input.answer,
      }
    },
  )
  .handler(async ({ data }): Promise<PreliminaryQuestionResult | ActionFailure> => {
    if ('kind' in data) return data
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).previewActivityQuestion(
        access.accessToken,
        data.ids,
        data.questionKey,
        data.activityRevision,
        data.answer,
      )
    } catch (error) {
      return actionFailure(error)
    }
  })

export function useActivityPage(props: ActivityPageProps) {
  const injected = 'activity' in props
  const goalId = injected ? null : props.goalId
  const skillId = injected ? null : props.skillId
  const competencyId = injected ? null : props.competencyId
  const activityId = injected ? null : props.activityId
  const routeIds: ActivityRouteIds | null = useMemo(
    () =>
      goalId && skillId && competencyId && activityId
        ? { goalId, skillId, competencyId, activityId }
        : null,
    [activityId, competencyId, goalId, skillId],
  )
  const onNavigateToAttempt = injected ? undefined : props.onNavigateToAttempt
  const onNavigateToDiagnostic = injected ? undefined : props.onNavigateToDiagnostic
  const onSessionExpired = injected ? undefined : props.onSessionExpired
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<readonly ActivityAnswer[]>([])
  const [feedback, setFeedback] = useState<PreliminaryQuestionResult | null>(null)
  const [isAssessing, setIsAssessing] = useState(false)
  const [hasFeedbackError, setHasFeedbackError] = useState(false)
  const [frozenAnswer, setFrozenAnswer] = useState<ActivityAnswer | null>(null)
  const feedbackRequestRef = useRef(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [hasSubmissionError, setHasSubmissionError] = useState(false)
  const [unsentAnswers, setUnsentAnswers] = useState(false)
  const submissionKeyRef = useRef<string | null>(null)
  const didSubmitRef = useRef(false)
  const activityQuery = useQuery({
    queryKey: ['learning', 'activity', ...(routeIds ? Object.values(routeIds) : [])],
    enabled: routeIds !== null,
    queryFn: async () => {
      if (!routeIds) throw new Error('Missing Activity route IDs')
      const result = await getActivityAction({ data: routeIds })
      if (isActionFailure(result)) throw mapActionFailure(result)
      return result
    },
    retry: false,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    staleTime: 0,
  })
  const activity = injected ? props.activity : (activityQuery.data ?? null)
  const isMixedActivity = Boolean(activity?.activityRevision)
  const isRouteError = activityQuery.isError && !injected
  const isPrivateAbsence =
    activityQuery.error instanceof RestError && activityQuery.error.statusCode === 404
  const isSessionRejected = activityQuery.error instanceof AuthError

  useEffect(() => {
    if (isSessionRejected) onSessionExpired?.()
  }, [isSessionRejected, onSessionExpired])

  useEffect(() => {
    if (!routeIds || !activity?.unresolvedAttemptId) return
    if (activity.isDiagnostic) onNavigateToDiagnostic?.()
    else onNavigateToAttempt?.(activity.unresolvedAttemptId, true)
  }, [
    activity?.unresolvedAttemptId,
    activity?.isDiagnostic,
    onNavigateToAttempt,
    onNavigateToDiagnostic,
    routeIds,
  ])

  const onUnsentAnswersChange =
    !injected && 'onUnsentAnswersChange' in props
      ? props.onUnsentAnswersChange
      : injected
        ? props.onUnsentAnswersChange
        : undefined
  const currentQuestion = activity?.questions[currentQuestionIndex] ?? null
  const currentAnswer = answers.find(
    (answer) => answer.questionKey === currentQuestion?.key,
  )
  const selectedOptionKeys =
    currentAnswer && 'selectedOptionKeys' in currentAnswer
      ? currentAnswer.selectedOptionKeys
      : []
  const hasValidSelection = Boolean(
    activity?.canSubmit &&
      currentQuestion &&
      currentQuestion.kind !== 'javascript_stdin' &&
      selectedOptionKeys.length > 0 &&
      selectedOptionKeys.every((key) =>
        currentQuestion.options.some((option) => option.key === key),
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
      currentQuestion.kind === 'javascript_stdin' ||
      isSubmitting ||
      isAssessing ||
      feedback ||
      frozenAnswer ||
      isSubmissionLocked ||
      !currentQuestion.options.some((option) => option.key === optionKey)
    )
      return
    const existing = answers.find((answer) => answer.questionKey === currentQuestion.key)
    const previous =
      existing && 'selectedOptionKeys' in existing ? existing.selectedOptionKeys : []
    const selectedOptionKeys =
      currentQuestion.kind === 'single_choice'
        ? [optionKey]
        : previous.includes(optionKey)
          ? previous.filter((key) => key !== optionKey)
          : [...previous, optionKey]
    const answer: ActivityAnswer = {
      ...(isMixedActivity ? { kind: currentQuestion.kind } : {}),
      questionKey: currentQuestion.key,
      selectedOptionKeys,
    }
    setAnswers((current) => [
      ...current.filter((item) => item.questionKey !== answer.questionKey),
      answer,
    ])
    setUnsentAnswers(true)
    setHasFeedbackError(false)
  }

  function handleCodeFilesChange(files: readonly { path: string; content: string }[]) {
    if (
      !currentQuestion ||
      currentQuestion.kind !== 'javascript_stdin' ||
      feedback ||
      frozenAnswer ||
      isAssessing
    )
      return
    const answer: CodeAnswer = {
      kind: 'javascript_stdin',
      questionKey: currentQuestion.key,
      files: files.map((file) => ({ ...file })),
    }
    setAnswers((current) => [
      ...current.filter((item) => item.questionKey !== answer.questionKey),
      answer,
    ])
    setUnsentAnswers(true)
    setHasFeedbackError(false)
  }

  async function handleAssessCode(files: readonly { path: string; content: string }[]) {
    if (!currentQuestion || currentQuestion.kind !== 'javascript_stdin') return
    const answer: CodeAnswer = {
      kind: 'javascript_stdin',
      questionKey: currentQuestion.key,
      files: files.map((file) => ({ ...file })),
    }
    await assess(answer)
  }

  async function assess(answer: ActivityAnswer, reevaluate = false) {
    if (
      !activity ||
      !currentQuestion ||
      isAssessing ||
      (feedback && !reevaluate) ||
      !activity.activityRevision
    )
      return
    const request = ++feedbackRequestRef.current
    const snapshot: ActivityAnswer =
      answer.kind === 'javascript_stdin'
        ? { ...answer, files: answer.files.map((file) => ({ ...file })) }
        : { ...answer, selectedOptionKeys: [...answer.selectedOptionKeys] }
    setFrozenAnswer(snapshot)
    setIsAssessing(true)
    setHasFeedbackError(false)
    try {
      const result = injected
        ? await props.onPreview?.(
            currentQuestion.key,
            activity.activityRevision,
            snapshot,
          )
        : await previewActivityQuestionAction({
            data: {
              ...routeIds,
              questionKey: currentQuestion.key,
              activityRevision: activity.activityRevision,
              answer: snapshot,
            },
          })
      if (!result || isActionFailure(result))
        throw result ? mapActionFailure(result) : new Error('Preview unavailable')
      if (request !== feedbackRequestRef.current) return
      setFeedback(result)
      setAnswers((current) => [
        ...current.filter((item) => item.questionKey !== snapshot.questionKey),
        snapshot,
      ])
      setUnsentAnswers(true)
    } catch {
      if (request === feedbackRequestRef.current) setHasFeedbackError(true)
    } finally {
      if (request === feedbackRequestRef.current) setIsAssessing(false)
    }
  }

  async function handleSubmit() {
    if (
      !activity ||
      !isLastQuestion ||
      (isMixedActivity && (!feedback || feedback.status !== 'conclusive')) ||
      answers.length !== activity.questions.length
    )
      return
    const submissionAnswers = activity.questions.map((question) =>
      answers.find((answer) => answer.questionKey === question.key),
    )
    if (submissionAnswers.some((answer) => !answer)) return
    if (!submissionKeyRef.current)
      submissionKeyRef.current = globalThis.crypto.randomUUID()
    setIsSubmitting(true)
    setHasSubmissionError(false)
    try {
      const submission: ChoiceSubmission = {
        answers: submissionAnswers as ActivityAnswer[],
        ...(activity.activityRevision
          ? { activityRevision: activity.activityRevision }
          : {}),
        submissionKey: submissionKeyRef.current,
      }
      const result = injected
        ? await props.onSubmit(submission)
        : await submitActivityAction({ data: { ...routeIds, submission } })
      if (isActionFailure(result)) throw mapActionFailure(result)
      didSubmitRef.current = true
      setUnsentAnswers(false)
      onUnsentAnswersChange?.(false)
      if (!injected && routeIds) {
        if (result.isDiagnostic || activity.isDiagnostic) onNavigateToDiagnostic?.()
        else onNavigateToAttempt?.(result.attemptId)
      }
    } catch {
      setHasSubmissionError(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleContinue() {
    if (!activity || !currentQuestion || isSubmitting || isAssessing) return
    if (!isMixedActivity) {
      if (!hasValidSelection) return
      if (isLastQuestion) void handleSubmit()
      else
        setCurrentQuestionIndex((index) =>
          Math.min(index + 1, activity.questions.length - 1),
        )
      return
    }
    if (!feedback) {
      if (frozenAnswer) {
        void assess(frozenAnswer, true)
        return
      }
      if (currentQuestion.kind !== 'javascript_stdin' && hasValidSelection) {
        void assess({
          kind: currentQuestion.kind,
          questionKey: currentQuestion.key,
          selectedOptionKeys,
        })
      }
      return
    }
    if (feedback.status !== 'conclusive') {
      setFeedback(null)
      if (frozenAnswer) void assess(frozenAnswer, true)
      return
    }
    if (isLastQuestion) {
      void handleSubmit()
      return
    }
    feedbackRequestRef.current += 1
    setFeedback(null)
    setFrozenAnswer(null)
    setCurrentQuestionIndex((index) => Math.min(index + 1, activity.questions.length - 1))
  }

  return {
    activity,
    runnerFactory: props.runnerFactory,
    isMixedActivity,
    canContinue:
      !isSubmitting &&
      !isAssessing &&
      (feedback !== null || frozenAnswer !== null || hasValidSelection),
    feedback,
    frozenAnswer,
    isAssessing,
    hasFeedbackError,
    handleAssessCode,
    handleCodeFilesChange,
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

export type ActivityPageController = ReturnType<typeof useActivityPage>

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
  const submission = value.submission
  return (
    isRouteIds(value) &&
    isRecord(submission) &&
    typeof submission.submissionKey === 'string' &&
    submission.submissionKey.length > 0 &&
    (submission.activityRevision === undefined ||
      submission.activityRevision === null ||
      (typeof submission.activityRevision === 'string' &&
        submission.activityRevision.length > 0)) &&
    Array.isArray(submission.answers) &&
    submission.answers.every(
      (answer: unknown) =>
        isRecord(answer) &&
        isQuestionKey(answer.questionKey) &&
        (submission.activityRevision
          ? isActivityAnswer(answer, answer.questionKey)
          : isLegacyChoiceAnswer(answer, answer.questionKey)),
    )
  )
}

function isLegacyChoiceAnswer(
  value: unknown,
  questionKey: string,
): value is ActivityAnswer {
  return (
    isRecord(value) &&
    value.questionKey === questionKey &&
    Array.isArray(value.selectedOptionKeys) &&
    value.selectedOptionKeys.every((key: unknown) => typeof key === 'string')
  )
}

function isActivityAnswer(value: unknown, questionKey: string): value is ActivityAnswer {
  if (!isRecord(value) || value.questionKey !== questionKey) return false
  if (value.kind === 'javascript_stdin') {
    return (
      Array.isArray(value.files) &&
      value.files.every(
        (file: unknown) =>
          isRecord(file) &&
          typeof file.path === 'string' &&
          typeof file.content === 'string',
      )
    )
  }
  return (
    (value.kind === 'single_choice' || value.kind === 'multiple_selection') &&
    Array.isArray(value.selectedOptionKeys) &&
    value.selectedOptionKeys.every((key: unknown) => typeof key === 'string')
  )
}

function isIdentifier(value: unknown): value is string {
  return typeof value === 'string' && COMPETENCY_DETAIL_ID_PATTERN.test(value)
}

function isQuestionKey(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0 && value.length <= 128
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export type ChoiceQuestionProps = {
  question: ChoiceQuestion
  activityTitle?: string
  questionNumber: number
  totalQuestions: number
  difficulty?: ActivityDifficulty
  selectedOptionKeys: readonly string[]
  onToggleOption: (optionKey: string) => void
  disabled?: boolean
}
