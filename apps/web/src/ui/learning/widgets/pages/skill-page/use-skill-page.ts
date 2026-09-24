import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import { CurriculumGapError } from '@/core/learning/curriculum-gap-error'
import type { DiagnosticOverview } from '@/core/learning/goal-detail'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { getGoalDetailAction } from '@/ui/learning/widgets/pages/goal-detail-page/use-goal-detail-page'

export type SkillPageProps = { goalId: string; skillId: string }
type ActionFailure = {
  kind: 'unauthorized' | 'not-found' | 'unavailable' | 'curriculum-gap'
}

export const getDiagnosticAction = createServerFn({ method: 'GET' })
  .validator((input: SkillPageProps) => input)
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
      ).getDiagnostic(access.accessToken, data.goalId, data.skillId)
    } catch (error) {
      if (error instanceof RestError && error.statusCode === 401)
        return { kind: 'unauthorized' }
      if (error instanceof RestError && error.statusCode === 404)
        return { kind: 'not-found' }
      return { kind: 'unavailable' }
    }
  })

export const startSkillAction = createServerFn({ method: 'POST' })
  .validator((input: SkillPageProps) => input)
  .handler(async ({ data }): Promise<{ ok: true } | ActionFailure> => {
    if (
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.goalId) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.skillId)
    )
      return { kind: 'not-found' }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).startSkill(access.accessToken, data.goalId, data.skillId)
      return { ok: true }
    } catch (error) {
      if (error instanceof CurriculumGapError) return { kind: 'curriculum-gap' }
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
}

export const retryDiagnosticAction = createServerFn({ method: 'POST' })
  .validator((input: RetryDiagnosticInput) => input)
  .handler(async ({ data }): Promise<{ ok: true } | ActionFailure> => {
    if (!Object.values(data).every((id) => COMPETENCY_DETAIL_ID_PATTERN.test(id))) {
      return { kind: 'not-found' }
    }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).retryDiagnosticEvaluation(access.accessToken, data)
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
  const { navigateTo } = useNavigation()
  const [isStarting, setIsStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const [isRetrying, setIsRetrying] = useState(false)
  const [retryError, setRetryError] = useState(false)
  const goalQuery = useQuery({
    queryKey: ['learning', 'goal-detail', props.goalId],
    queryFn: async () => {
      const result = await getGoalDetailAction({ data: props.goalId })
      if ('kind' in result) throw result
      return result
    },
    retry: false,
  })
  const diagnosticQuery = useQuery({
    queryKey: ['learning', 'diagnostic', props.goalId, props.skillId],
    queryFn: async () => {
      const result = await getDiagnosticAction({ data: props })
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
      (query.state.data.pendingAttemptStatus === 'pending' ||
        !query.state.data.nextActivityId)
        ? 3000
        : false,
    refetchOnWindowFocus: true,
  })

  useEffect(() => {
    if (diagnosticQuery.error instanceof AuthError) void navigateTo('login')
  }, [diagnosticQuery.error, navigateTo])

  async function handleStart() {
    if (isStarting) return
    setIsStarting(true)
    setStartError(null)
    const result = await startSkillAction({ data: props })
    setIsStarting(false)
    if ('kind' in result) {
      setStartError(
        result.kind === 'curriculum-gap'
          ? 'O Currículo desta Habilidade ainda não tem cobertura suficiente para iniciar o diagnóstico.'
          : 'Não foi possível iniciar a Habilidade. Tente novamente.',
      )
      return
    }
    await diagnosticQuery.refetch()
  }

  async function handleRetryDiagnostic() {
    const diagnostic = diagnosticQuery.data
    if (
      isRetrying ||
      diagnostic?.pendingAttemptStatus !== 'failed' ||
      !diagnostic.pendingAttemptId ||
      !diagnostic.nextCompetencyId ||
      !diagnostic.nextActivityId
    )
      return
    setIsRetrying(true)
    setRetryError(false)
    const result = await retryDiagnosticAction({
      data: {
        ...props,
        competencyId: diagnostic.nextCompetencyId,
        activityId: diagnostic.nextActivityId,
        attemptId: diagnostic.pendingAttemptId,
      },
    })
    setIsRetrying(false)
    if ('kind' in result) {
      setRetryError(true)
      return
    }
    await diagnosticQuery.refetch()
  }

  return {
    diagnostic: diagnosticQuery.data ?? null,
    skillName:
      goalQuery.data?.skills.find((skill) => skill.skillId === props.skillId)
        ?.skillName ?? 'Habilidade',
    isLoading: diagnosticQuery.isPending || goalQuery.isPending,
    isPrivateAbsence:
      diagnosticQuery.error instanceof RestError &&
      diagnosticQuery.error.statusCode === 404,
    isRecoverableError:
      Boolean(diagnosticQuery.error) && !(diagnosticQuery.error instanceof AuthError),
    isStarting,
    startError,
    isRetrying,
    retryError,
    handleStart,
    handleRetryDiagnostic,
    handleRetry: diagnosticQuery.refetch,
  }
}
