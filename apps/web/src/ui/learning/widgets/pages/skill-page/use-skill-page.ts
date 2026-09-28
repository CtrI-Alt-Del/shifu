import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import { ROUTES } from '@/constants/routes'
import { CurriculumGapError } from '@/core/learning/curriculum-gap-error'
import type { DiagnosticOverview } from '@/core/learning/goal-detail'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { getGoalDetail } from '@/provision/learning/get-goal-detail'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { useRemoveSkillAction } from '@/ui/learning/hooks/use-remove-skill-action'
import {
  clearDiagnosticRun,
  getDiagnosticRun,
  setDiagnosticRun,
} from '@/ui/learning/diagnostic-run-session'

export type SkillPageProps = { goalId: string; skillId: string }
type GetDiagnosticInput = SkillPageProps & { diagnosticRunId?: string }
type StartSkillInput = SkillPageProps & { entryKey: string }
type ActionFailure = {
  kind: 'unauthorized' | 'not-found' | 'unavailable' | 'curriculum-gap' | 'stale-run'
}

export const getDiagnosticAction = createServerFn({ method: 'GET' })
  .validator((input: GetDiagnosticInput) => input)
  .handler(async ({ data }): Promise<DiagnosticOverview | ActionFailure> => {
    if (
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.goalId) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.skillId)
    )
      return { kind: 'not-found' }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).getDiagnostic(access.accessToken, data.goalId, data.skillId, data.diagnosticRunId)
    } catch (error) {
      if (error instanceof RestError && error.statusCode === 401)
        return { kind: 'unauthorized' }
      if (error instanceof RestError && error.statusCode === 404)
        return { kind: 'not-found' }
      if (error instanceof RestError && error.statusCode === 409)
        return { kind: 'stale-run' }
      return { kind: 'unavailable' }
    }
  })

export const startSkillAction = createServerFn({ method: 'POST' })
  .validator((input: StartSkillInput) => input)
  .handler(async ({ data }): Promise<{ diagnosticRunId: string } | ActionFailure> => {
    if (
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.goalId) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.skillId)
    )
      return { kind: 'not-found' }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      const response = await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).startSkill(access.accessToken, data.goalId, data.skillId, data.entryKey)
      return { diagnosticRunId: response.diagnosticRunId }
    } catch (error) {
      if (error instanceof CurriculumGapError) return { kind: 'curriculum-gap' }
      if (error instanceof RestError && error.statusCode === 401)
        return { kind: 'unauthorized' }
      if (error instanceof RestError && error.statusCode === 404)
        return { kind: 'not-found' }
      return { kind: 'unavailable' }
    }
  })

export const completeDiagnosticAction = createServerFn({ method: 'POST' })
  .validator((input: SkillPageProps & { diagnosticRunId: string }) => input)
  .handler(async ({ data }): Promise<{ ok: true } | ActionFailure> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).completeDiagnostic(
        access.accessToken,
        data.goalId,
        data.skillId,
        data.diagnosticRunId,
      )
      return { ok: true }
    } catch (error) {
      if (error instanceof RestError && error.statusCode === 401)
        return { kind: 'unauthorized' }
      if (error instanceof RestError && error.statusCode === 404)
        return { kind: 'not-found' }
      return { kind: 'unavailable' }
    }
  })

type RetryDiagnosticInput = SkillPageProps & {
  competencyId: string
  activityId: string
  attemptId: string
  diagnosticRunId: string
}

export const retryDiagnosticAction = createServerFn({ method: 'POST' })
  .validator((input: RetryDiagnosticInput) => input)
  .handler(async ({ data }): Promise<{ ok: true } | ActionFailure> => {
    if (
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.goalId) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.skillId) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.competencyId) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.activityId) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.attemptId) ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
        data.diagnosticRunId,
      )
    ) {
      return { kind: 'not-found' }
    }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).retryDiagnosticEvaluation(access.accessToken, data, data.diagnosticRunId)
      return { ok: true }
    } catch (error) {
      if (error instanceof RestError && error.statusCode === 401)
        return { kind: 'unauthorized' }
      if (error instanceof RestError && error.statusCode === 404)
        return { kind: 'not-found' }
      return { kind: 'unavailable' }
    }
  })

export function useSkillPage(props: SkillPageProps) {
  const { navigateTo, navigateToGoalDetail } = useNavigation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isRemovalDialogOpen, setIsRemovalDialogOpen] = useState(false)
  const removalTriggerRef = useRef<HTMLElement | null>(null)
  const isRemovalSubmittingRef = useRef(false)
  const [isStarting, setIsStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const [isRetrying, setIsRetrying] = useState(false)
  const [isCompleting, setIsCompleting] = useState(false)
  const [completionError, setCompletionError] = useState(false)
  const completionRunRef = useRef<string | null>(null)
  const activityNavigationRef = useRef<string | null>(null)
  const entryKeyRef = useRef<string | null>(null)
  const entryStartedRef = useRef(false)
  const [retryError, setRetryError] = useState(false)
  const { isRemovingSkill, removeSkill, removeSkillError, resetRemoveSkill } =
    useRemoveSkillAction(props)
  const goalQuery = useQuery({
    queryKey: ['learning', 'goal-detail', props.goalId],
    queryFn: async () => {
      const result = await getGoalDetail({ data: { goalId: props.goalId } })
      if (result.kind !== 'success') throw result
      return result.detail
    },
    retry: false,
  })
  const diagnosticQuery = useQuery({
    queryKey: ['learning', 'diagnostic', props.goalId, props.skillId],
    queryFn: async () => {
      const run = getDiagnosticRun(props.goalId, props.skillId)
      const result = await getDiagnosticAction({
        data: { ...props, diagnosticRunId: run?.diagnosticRunId },
      })
      if ('kind' in result) {
        if (result.kind === 'unauthorized')
          throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
            statusCode: 401,
          })
        throw new RestError(
          'Habilidade indisponível.',
          result.kind === 'not-found' ? 404 : 503,
        )
      }
      return result
    },
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.status === 'diagnosing' &&
      query.state.data.runState === 'active' &&
      query.state.data.pendingAttemptStatus === 'pending'
        ? 3000
        : false,
    refetchOnWindowFocus: true,
  })

  const handleStart = useCallback(async () => {
    if (isStarting) return
    if (!entryKeyRef.current) entryKeyRef.current = globalThis.crypto.randomUUID()
    setIsStarting(true)
    setStartError(null)
    let result: Awaited<ReturnType<typeof startSkillAction>>
    try {
      result = await startSkillAction({
        data: {
          goalId: props.goalId,
          skillId: props.skillId,
          entryKey: entryKeyRef.current,
        },
      })
    } catch {
      setIsStarting(false)
      entryStartedRef.current = false
      setStartError('Não foi possível iniciar o diagnóstico. Tente novamente.')
      return
    }
    setIsStarting(false)
    if ('kind' in result) {
      entryStartedRef.current = false
      setStartError(
        result.kind === 'curriculum-gap'
          ? 'O Currículo desta Habilidade ainda não tem cobertura suficiente para iniciar o diagnóstico.'
          : 'Não foi possível iniciar a Habilidade. Tente novamente.',
      )
      return
    }
    setDiagnosticRun(props.goalId, props.skillId, result.diagnosticRunId)
    entryKeyRef.current = null
    entryStartedRef.current = false
    try {
      await diagnosticQuery.refetch()
    } catch {
      setStartError(
        'O diagnóstico foi iniciado, mas não foi possível carregar a Atividade.',
      )
    }
  }, [diagnosticQuery.refetch, isStarting, props.goalId, props.skillId])

  useEffect(() => {
    if (diagnosticQuery.error instanceof AuthError) void navigateTo('login')
  }, [diagnosticQuery.error, navigateTo])

  useEffect(() => {
    if (
      diagnosticQuery.data?.status !== 'diagnosing' ||
      diagnosticQuery.data.runState !== 'requires_entry' ||
      startError ||
      getDiagnosticRun(props.goalId, props.skillId) ||
      entryStartedRef.current
    )
      return
    entryStartedRef.current = true
    void handleStart()
  }, [diagnosticQuery.data, props.goalId, props.skillId, startError, handleStart])

  useEffect(() => {
    const diagnostic = diagnosticQuery.data
    const run = getDiagnosticRun(props.goalId, props.skillId)
    if (
      diagnostic?.status !== 'diagnosing' ||
      diagnostic.runState !== 'active' ||
      !diagnostic.nextCompetencyId ||
      !diagnostic.nextActivityId ||
      !run
    )
      return

    const navigationKey = `${run.diagnosticRunId}:${diagnostic.nextCompetencyId}:${diagnostic.nextActivityId}`
    if (activityNavigationRef.current === navigationKey) return
    activityNavigationRef.current = navigationKey
    window.scrollTo(0, 0)
    void navigateTo('learningActivity', {
      goalId: props.goalId,
      skillId: props.skillId,
      competencyId: diagnostic.nextCompetencyId,
      activityId: diagnostic.nextActivityId,
    })
  }, [diagnosticQuery.data, navigateTo, props.goalId, props.skillId])

  useEffect(() => {
    const diagnostic = diagnosticQuery.data
    const run = getDiagnosticRun(props.goalId, props.skillId)
    if (
      !diagnostic?.readyToComplete ||
      diagnostic.runState !== 'ready_to_complete' ||
      !run ||
      isCompleting ||
      completionError ||
      completionRunRef.current === run.diagnosticRunId
    )
      return
    completionRunRef.current = run.diagnosticRunId
    setIsCompleting(true)
    void completeDiagnosticAction({
      data: { ...props, diagnosticRunId: run.diagnosticRunId },
    })
      .then(async (result) => {
        setIsCompleting(false)
        if ('kind' in result) {
          setCompletionError(true)
          return
        }
        clearDiagnosticRun(props.goalId, props.skillId)
        await navigate({ to: ROUTES.learningDiagnosticResult, params: props })
      })
      .catch(() => {
        setIsCompleting(false)
        setCompletionError(true)
      })
  }, [diagnosticQuery.data, isCompleting, completionError, navigate, props])

  async function handleRetryDiagnostic() {
    const diagnostic = diagnosticQuery.data
    const run = getDiagnosticRun(props.goalId, props.skillId)
    if (
      isRetrying ||
      diagnostic?.pendingAttemptStatus !== 'failed' ||
      !diagnostic.pendingAttemptId ||
      !diagnostic.nextCompetencyId ||
      !diagnostic.nextActivityId ||
      !run
    )
      return
    setIsRetrying(true)
    setRetryError(false)
    try {
      const result = await retryDiagnosticAction({
        data: {
          ...props,
          competencyId: diagnostic.nextCompetencyId,
          activityId: diagnostic.nextActivityId,
          attemptId: diagnostic.pendingAttemptId,
          diagnosticRunId: run.diagnosticRunId,
        },
      })
      if ('kind' in result) {
        setRetryError(true)
        return
      }
      await diagnosticQuery.refetch()
    } catch {
      setRetryError(true)
    } finally {
      setIsRetrying(false)
    }
  }

  async function handleRetryCompletion() {
    completionRunRef.current = null
    setCompletionError(false)
    await diagnosticQuery.refetch()
  }

  function handleOpenRemovalDialog(trigger?: HTMLButtonElement) {
    if (trigger) removalTriggerRef.current = trigger
    resetRemoveSkill()
    setIsRemovalDialogOpen(true)
  }

  function handleCancelRemoval() {
    if (isRemovingSkill) return
    setIsRemovalDialogOpen(false)
    resetRemoveSkill()
  }

  async function handleConfirmRemoval() {
    if (isRemovingSkill || isRemovalSubmittingRef.current) return
    isRemovalSubmittingRef.current = true
    try {
      await removeSkill()
      await queryClient.invalidateQueries({
        queryKey: ['learning', 'goal-detail', props.goalId],
      })
      navigateToGoalDetail(props.goalId)
    } catch {
      // Mutation state owns the recoverable user-facing error.
    } finally {
      isRemovalSubmittingRef.current = false
    }
  }

  return {
    diagnostic: diagnosticQuery.data ?? null,
    hasDiagnosticRun: Boolean(getDiagnosticRun(props.goalId, props.skillId)),
    diagnosticRunId:
      getDiagnosticRun(props.goalId, props.skillId)?.diagnosticRunId ?? null,
    skillName:
      goalQuery.data?.skills.find((skill) => skill.skillId === props.skillId)
        ?.skillName ??
      goalQuery.data?.skills.find((skill) => skill.skillId === props.skillId)?.name ??
      'Habilidade',
    isLoading: diagnosticQuery.isPending || goalQuery.isPending,
    isPrivateAbsence:
      diagnosticQuery.error instanceof RestError &&
      diagnosticQuery.error.statusCode === 404,
    isRecoverableError:
      Boolean(diagnosticQuery.error) && !(diagnosticQuery.error instanceof AuthError),
    isStarting,
    startError,
    isRetrying,
    isCompleting,
    completionError,
    retryError,
    isRemovalDialogOpen,
    isRemovingSkill,
    removeSkillError,
    removalTriggerRef,
    handleStart,
    handleRetryDiagnostic,
    handleRetryCompletion,
    handleOpenRemovalDialog,
    handleCancelRemoval,
    handleConfirmRemoval,
    handleRetry: diagnosticQuery.refetch,
  }
}
