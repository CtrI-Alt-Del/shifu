import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import type {
  PlanningGoalCreationRequest,
  PlanningOperation,
  PlanningOperationStage,
  PlanningQuestion,
  PlanningSession,
} from '@/core/intelligence/planning-session'
import { PlanningRequestError } from '@/ui/intelligence/hooks/planning-request-error'
import { useAnswerPlanningQuestionsAction } from '@/ui/intelligence/hooks/use-answer-planning-questions-action'
import { useCancelPlanningAction } from '@/ui/intelligence/hooks/use-cancel-planning-action'
import { useConfirmPlanningAction } from '@/ui/intelligence/hooks/use-confirm-planning-action'
import { HOME_GOALS_QUERY_KEY } from '@/ui/intelligence/hooks/home-goals-query-key'
import {
  planningSessionQueryKey,
  usePlanningSessionQuery,
} from '@/ui/intelligence/hooks/use-planning-session-query'
import { useRestartPlanningAction } from '@/ui/intelligence/hooks/use-restart-planning-action'
import { useRetryPlanningAction } from '@/ui/intelligence/hooks/use-retry-planning-action'
import { consumePlanningEntry } from '@/ui/intelligence/planning-entry'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import {
  type GoalCreationState,
  IDLE_GOAL_CREATION,
} from './planning-proposal-review/use-planning-proposal-review'

export type PlannerPageProps = {
  planningId: string
}

export type PlannerView =
  | 'loading'
  | 'request-error'
  | 'not-found'
  | 'interview'
  | 'processing'
  | 'failed'
  | 'out-of-scope'
  | 'unsupported'
  | 'validation-failed'
  | 'proposal'

export type PlannerStepState = 'current' | 'answered' | 'pending'

export type PlannerStep = {
  number: number
  questionId: string
  state: PlannerStepState
}

export type PlannerProcessingStage = {
  title: string
  support: string
  busyLabel: string
}

type PlannerDraft = {
  batchId: string | null
  answers: Record<string, string[]>
  index: number
}

type LeaveRoute = 'root' | 'learningGoalsNew'

const EMPTY_DRAFT: PlannerDraft = { batchId: null, answers: {}, index: 0 }

const STAGE_COPY: Record<PlanningOperationStage, PlannerProcessingStage> = {
  analyzing: {
    title: 'Analisando seu objetivo…',
    support: 'Estamos entendendo o que você quer alcançar.',
    busyLabel: 'Analisando…',
  },
  retrieving: {
    title: 'Consultando o Currículo…',
    support: 'Estamos buscando habilidades relacionadas ao que você quer aprender.',
    busyLabel: 'Consultando…',
  },
  interviewing: {
    title: 'Preparando o próximo passo…',
    support: 'Estamos verificando o que falta esclarecer.',
    busyLabel: 'Processando…',
  },
  composing: {
    title: 'Montando sua proposta…',
    support: 'Estamos selecionando habilidades para o seu objetivo.',
    busyLabel: 'Montando proposta…',
  },
}

const ANSWERED_INTERVIEWING_SUPPORT =
  'Suas respostas foram enviadas. Estamos verificando o que falta esclarecer.'
const SUBMISSION_ERROR_MESSAGE =
  'Não foi possível enviar suas respostas agora. Suas escolhas continuam nesta página; tente novamente.'
const RETRY_ERROR_MESSAGE =
  'Não foi possível tentar novamente agora. Seu planejamento continua nesta página.'
const RESTART_ERROR_MESSAGE =
  'Não foi possível reiniciar o planejamento agora. Sua proposta continua nesta página; tente novamente.'
const REVIEW_GUIDANCE =
  'Você pode alterar esta resposta. Use as etapas para revisar as demais e enviar na última pergunta.'

export function usePlannerPage({ planningId }: PlannerPageProps) {
  const queryClient = useQueryClient()
  const { navigateTo, navigateToGoalDetail } = useNavigation()
  const [isLeaving, setIsLeaving] = useState(false)
  const [hasEntry] = useState(() => consumePlanningEntry(planningId))
  const [draft, setDraft] = useState<PlannerDraft>(EMPTY_DRAFT)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [restartErrorMessage, setRestartErrorMessage] = useState<string | null>(null)
  const [goalCreation, setGoalCreation] = useState<GoalCreationState>(IDLE_GOAL_CREATION)
  const questionHeadingRef = useRef<HTMLHeadingElement>(null)
  const previousFocusKeyRef = useRef<string | null>(null)
  const leavingRef = useRef(false)
  const leaveToRef = useRef(leaveTo)
  leaveToRef.current = leaveTo
  const operationRef = useRef(false)
  const isAbandoning = !hasEntry
  const isActive = hasEntry && !isLeaving
  const {
    planningSession,
    planningSessionError,
    isLoadingPlanningSession,
    refetchPlanningSession,
  } = usePlanningSessionQuery(planningId, isActive)
  const { answerPlanningQuestions, isAnsweringPlanningQuestions } =
    useAnswerPlanningQuestionsAction(planningId)
  const { retryPlanning, isRetryingPlanning } = useRetryPlanningAction(planningId)
  const { restartPlanning, isRestartingPlanning } = useRestartPlanningAction(planningId)
  const { cancelPlanning, isCancellingPlanning } = useCancelPlanningAction(planningId)
  const { confirmPlanning, isConfirmingPlanning } = useConfirmPlanningAction(planningId)

  const batch = planningSession?.status === 'interview' ? planningSession.batch : null
  const batchId = batch?.id ?? null
  const activeDraft = draft.batchId === batchId ? draft : { ...EMPTY_DRAFT, batchId }
  const questions = batch?.questions ?? []
  const currentIndex = Math.min(activeDraft.index, Math.max(questions.length - 1, 0))
  const currentQuestion = questionAt(questions, currentIndex)
  const selectedOptionIds = currentQuestion
    ? (activeDraft.answers[currentQuestion.id] ?? [])
    : []
  const isBatchComplete =
    questions.length > 0 &&
    questions.every((question) => (activeDraft.answers[question.id] ?? []).length > 0)
  const isFirstStep = currentIndex === 0
  const isLastStep = questions.length > 0 && currentIndex === questions.length - 1
  const steps: PlannerStep[] = questions.map((question, index) => ({
    number: index + 1,
    questionId: question.id,
    state:
      index === currentIndex
        ? 'current'
        : (activeDraft.answers[question.id] ?? []).length > 0
          ? 'answered'
          : 'pending',
  }))
  const requestFailure =
    planningSessionError instanceof PlanningRequestError ? planningSessionError : null
  const view = resolveView({
    isAbandoning: isAbandoning || isLeaving,
    isLoading: isLoadingPlanningSession,
    hasError: planningSessionError !== null,
    isNotFound: requestFailure?.kind === 'not-found',
    session: planningSession,
  })
  const isSubmitting = isAnsweringPlanningQuestions
  const isRetrying = isRetryingPlanning
  const isRestarting = isRestartingPlanning
  const isCancelling = isCancellingPlanning
  const canSubmit = view === 'interview' && isLastStep && isBatchComplete && !isSubmitting
  const focusKey = currentQuestion ? `${batchId}:${currentQuestion.id}` : null

  useEffect(() => {
    // The entry marker is read once on mount; leaving happens exactly once.
    if (isAbandoning) void leaveToRef.current('root', true)
  }, [isAbandoning])

  useEffect(() => {
    if (requestFailure?.kind !== 'unauthorized') return
    void navigateTo('login')
  }, [requestFailure, navigateTo])

  useEffect(() => {
    const previousKey = previousFocusKeyRef.current
    previousFocusKeyRef.current = focusKey
    if (!focusKey || previousKey === null || previousKey === focusKey) return
    questionHeadingRef.current?.focus()
  }, [focusKey])

  function updateAnswers(questionId: string, optionIds: string[]) {
    setDraft({
      batchId,
      index: currentIndex,
      answers: { ...activeDraft.answers, [questionId]: optionIds },
    })
    setErrorMessage(null)
  }

  function handleSelectSingle(optionId: string) {
    if (!currentQuestion || isSubmitting) return
    if (!currentQuestion.options.some((option) => option.id === optionId)) return
    updateAnswers(currentQuestion.id, [optionId])
  }

  function handleToggleMultiple(optionId: string, checked: boolean) {
    if (!currentQuestion || isSubmitting) return
    const option = currentQuestion.options.find((candidate) => candidate.id === optionId)
    if (!option) return
    const previous = activeDraft.answers[currentQuestion.id] ?? []
    if (!checked) {
      updateAnswers(
        currentQuestion.id,
        previous.filter((selected) => selected !== optionId),
      )
      return
    }
    if (option.exclusive) {
      updateAnswers(currentQuestion.id, [optionId])
      return
    }
    const exclusiveIds = currentQuestion.options
      .filter((candidate) => candidate.exclusive)
      .map((candidate) => candidate.id)
    updateAnswers(currentQuestion.id, [
      ...previous.filter((selected) => !exclusiveIds.includes(selected)),
      optionId,
    ])
  }

  function handleGoToStep(index: number) {
    if (questions.length === 0) return
    const nextIndex = Math.min(Math.max(index, 0), questions.length - 1)
    setDraft({ ...activeDraft, batchId, index: nextIndex })
  }

  function handlePrevious() {
    handleGoToStep(currentIndex - 1)
  }

  function handleNext() {
    handleGoToStep(currentIndex + 1)
  }

  async function handleSubmitAnswers() {
    if (!canSubmit || !batch || operationRef.current) return
    operationRef.current = true
    setErrorMessage(null)
    try {
      const updated = await answerPlanningQuestions({
        batchId: batch.id,
        answers: batch.questions.map((question) => ({
          questionId: question.id,
          optionIds: activeDraft.answers[question.id] ?? [],
        })),
      })
      queryClient.setQueryData(planningSessionQueryKey(planningId), updated)
    } catch (error) {
      setErrorMessage(resolveOperationFailure(error, SUBMISSION_ERROR_MESSAGE))
    } finally {
      operationRef.current = false
    }
  }

  async function handleRetry() {
    if (operationRef.current || isRetrying) return
    if (view !== 'failed' && view !== 'validation-failed') return
    operationRef.current = true
    setErrorMessage(null)
    try {
      const updated = await retryPlanning()
      queryClient.setQueryData(planningSessionQueryKey(planningId), updated)
    } catch (error) {
      setErrorMessage(resolveOperationFailure(error, RETRY_ERROR_MESSAGE))
    } finally {
      operationRef.current = false
    }
  }

  async function handleRestart(initialIntent: string): Promise<boolean> {
    if (operationRef.current || isRestarting || view !== 'proposal') return false
    operationRef.current = true
    setRestartErrorMessage(null)
    try {
      const updated = await restartPlanning(initialIntent)
      setGoalCreation(IDLE_GOAL_CREATION)
      queryClient.setQueryData(planningSessionQueryKey(planningId), updated)
      return true
    } catch (error) {
      setRestartErrorMessage(resolveOperationFailure(error, RESTART_ERROR_MESSAGE))
      return false
    } finally {
      operationRef.current = false
    }
  }

  async function handleCreateGoal(request: PlanningGoalCreationRequest) {
    if (operationRef.current || view !== 'proposal') return
    operationRef.current = true
    setGoalCreation({ status: 'creating', message: null })
    try {
      // The backend uses its own proposal; only the edits and the key travel.
      const creation = await confirmPlanning({
        confirmationKey: request.confirmationKey,
        title: request.title,
        description: request.description,
      })
      await leaveToGoal(creation.goalId)
    } catch (error) {
      setGoalCreation(resolveGoalCreationFailure(error))
    } finally {
      operationRef.current = false
    }
  }

  function resolveGoalCreationFailure(error: unknown): GoalCreationState {
    if (error instanceof PlanningRequestError) {
      if (error.kind === 'unauthorized') {
        void navigateTo('login')
        return IDLE_GOAL_CREATION
      }
      if (error.kind === 'not-found') {
        // The planning expired or was discarded elsewhere; the page shows that state.
        void refetchPlanningSession()
        return IDLE_GOAL_CREATION
      }
      if (error.kind === 'unavailable') return { status: 'uncertain', message: null }
      return { status: 'failed', message: error.message }
    }
    return { status: 'uncertain', message: null }
  }

  async function leaveToGoal(goalId: string) {
    leavingRef.current = true
    setIsLeaving(true)
    await queryClient.invalidateQueries({ queryKey: HOME_GOALS_QUERY_KEY })
    queryClient.removeQueries({ queryKey: planningSessionQueryKey(planningId) })
    await navigateToGoalDetail(goalId)
  }

  function resolveOperationFailure(error: unknown, fallbackMessage: string) {
    if (error instanceof PlanningRequestError) {
      if (error.kind === 'unauthorized') {
        void navigateTo('login')
        return null
      }
      if (error.kind === 'not-found') {
        void refetchPlanningSession()
        return null
      }
      if (error.kind === 'conflict') void refetchPlanningSession()
      return error.kind === 'unavailable' ? fallbackMessage : error.message
    }
    return fallbackMessage
  }

  async function leaveTo(route: LeaveRoute, shouldCancel: boolean) {
    if (leavingRef.current) return
    leavingRef.current = true
    setIsLeaving(true)
    if (shouldCancel) {
      // Leaving is the learner's decision; a failed delete only leaves state to expire.
      await cancelPlanning().catch(() => undefined)
    }
    queryClient.removeQueries({ queryKey: planningSessionQueryKey(planningId) })
    await navigateTo(route)
  }

  async function handleCancel() {
    await leaveTo('root', true)
  }

  function handleReformulate() {
    void leaveTo('root', true)
  }

  function handleCreateManually() {
    void leaveTo('learningGoalsNew', true)
  }

  function handleReturnHome() {
    void leaveTo('root', false)
  }

  function handleRetryLoad() {
    setErrorMessage(null)
    void refetchPlanningSession()
  }

  return {
    view,
    intent: planningSession?.intent ?? null,
    generation: planningSession?.generation ?? 0,
    steps,
    stepLabel: stepLabelFor(currentIndex, questions.length, isBatchComplete, isLastStep),
    currentQuestion,
    selectedOptionIds,
    guidance: guidanceFor(currentQuestion, isLastStep, isBatchComplete),
    isFirstStep,
    isLastStep,
    isBatchComplete,
    canSubmit,
    processingStage:
      view === 'processing' && planningSession
        ? processingStageFor(planningSession)
        : null,
    proposal: view === 'proposal' ? (planningSession?.proposal ?? null) : null,
    errorMessage,
    restartErrorMessage,
    goalCreation,
    isSubmitting,
    isCreatingGoal: isConfirmingPlanning,
    isRetrying,
    isRestarting,
    isCancelling,
    isAbandoning,
    questionHeadingRef,
    handleSelectSingle,
    handleToggleMultiple,
    handleGoToStep,
    handlePrevious,
    handleNext,
    handleSubmitAnswers,
    handleCancel,
    handleRetry,
    handleRestart,
    handleCreateGoal,
    handleReformulate,
    handleCreateManually,
    handleRetryLoad,
    handleReturnHome,
  }
}

export type PlannerPageController = ReturnType<typeof usePlannerPage>

function questionAt(
  questions: PlanningQuestion[],
  index: number,
): PlanningQuestion | null {
  return questions[index] ?? null
}

function resolveView(input: {
  isAbandoning: boolean
  isLoading: boolean
  hasError: boolean
  isNotFound: boolean
  session: PlanningSession | null
}): PlannerView {
  if (input.isAbandoning || input.isLoading) return 'loading'
  if (input.hasError || !input.session) {
    return input.isNotFound ? 'not-found' : 'request-error'
  }
  const { status } = input.session
  if (status === 'interview') return input.session.batch ? 'interview' : 'request-error'
  if (status === 'proposal') return input.session.proposal ? 'proposal' : 'request-error'
  return status
}

function processingStageFor(session: PlanningSession): PlannerProcessingStage {
  const operation = session.operation
  const stage = operation?.stage ?? defaultStageFor(operation, session.answeredBatchCount)
  const copy = STAGE_COPY[stage]
  if (stage === 'interviewing' && operation?.kind === 'answer') {
    return { ...copy, support: ANSWERED_INTERVIEWING_SUPPORT }
  }
  return copy
}

function defaultStageFor(
  operation: PlanningOperation | null,
  answeredBatchCount: number,
): PlanningOperationStage {
  if (operation?.kind === 'answer') return 'interviewing'
  if (operation?.kind === 'retry' && answeredBatchCount > 0) return 'interviewing'
  return 'analyzing'
}

function stepLabelFor(
  index: number,
  total: number,
  isBatchComplete: boolean,
  isLastStep: boolean,
): string {
  if (total === 0) return ''
  const position = `${index + 1} de ${total}`
  return isBatchComplete && !isLastStep
    ? `Revisando pergunta ${position} · conjunto respondido`
    : `Pergunta ${position} deste conjunto`
}

function guidanceFor(
  question: PlanningQuestion | null,
  isLastStep: boolean,
  isBatchComplete: boolean,
): string {
  if (!question) return ''
  const prefix =
    question.kind === 'single'
      ? 'Escolha uma alternativa.'
      : 'Selecione uma ou mais alternativas.'
  if (isBatchComplete) {
    return isLastStep
      ? `${prefix} Todas as perguntas estão respondidas; revise as etapas antes de enviar.`
      : REVIEW_GUIDANCE
  }
  if (
    question.kind === 'multiple' &&
    question.options.some((option) => option.exclusive)
  ) {
    return `${prefix} “Não sei” não pode ser combinado com outras respostas.`
  }
  if (isLastStep) {
    return `${prefix} Responda todas as perguntas do conjunto para enviar.`
  }
  return `${prefix} Você poderá revisar as respostas antes de enviar este conjunto.`
}
