import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import type {
  ChoiceActivityDetail,
  ChoiceAttemptDetail,
} from '@/core/learning/choice-activity'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { getChoiceActivityAction } from '@/ui/learning/widgets/pages/choice-activity-page/use-choice-activity-page'
import type { ActivityRecommendation } from '@/core/learning/competency-detail'

export type ChoiceResultRouteProps = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
  attemptId: string
  onNavigateToActivity: () => void
  onOpenRecommendation: (recommendation: ActivityRecommendation) => void
  onSessionExpired: () => void
}

export type ChoiceResultRenderProps =
  | { state: 'loading' }
  | { state: 'private-absence' }
  | { state: 'error'; onRetryLoad: () => void }
  | {
      state: 'result'
      activity: ChoiceActivityDetail
      attempt: ChoiceAttemptDetail
      recommendation?: ActivityRecommendation | null
      onRetryEvaluation: () => Promise<void>
      onOpenRecommendation?: (recommendation: ActivityRecommendation) => void
      onReturnToActivity?: () => void
    }

export type ChoiceResultPageProps = ChoiceResultRenderProps | ChoiceResultRouteProps

type ActionFailure =
  | { kind: 'invalid-request' }
  | { kind: 'unauthorized' }
  | { kind: 'not-found' }
  | { kind: 'unavailable'; statusCode?: number }

type ChoiceResultRouteIds = Omit<
  ChoiceResultRouteProps,
  'onNavigateToActivity' | 'onOpenRecommendation' | 'onSessionExpired'
>
type ValidatedAttemptInput = ChoiceResultRouteIds | { kind: 'invalid-request' }

export const getChoiceAttemptAction = createServerFn({ method: 'GET' })
  .validator(
    (input: unknown): ValidatedAttemptInput =>
      isRouteInput(input) ? input : { kind: 'invalid-request' },
  )
  .handler(async ({ data }): Promise<ChoiceAttemptDetail | ActionFailure> => {
    if ('kind' in data) return data
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).getChoiceAttempt(access.accessToken, data)
    } catch (error) {
      return actionFailure(error)
    }
  })

export const retryChoiceEvaluationAction = createServerFn({ method: 'POST' })
  .validator(
    (input: unknown): ValidatedAttemptInput =>
      isRouteInput(input) ? input : { kind: 'invalid-request' },
  )
  .handler(async ({ data }): Promise<{ ok: true } | ActionFailure> => {
    if ('kind' in data) return data
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).retryChoiceEvaluation(access.accessToken, data)
      return { ok: true }
    } catch (error) {
      return actionFailure(error)
    }
  })

export function useChoiceResultPage(props: ChoiceResultPageProps) {
  const routeProps = isRoutePageProps(props) ? props : null
  const routeMode = routeProps !== null
  const legacyProps: ChoiceResultRenderProps | null = routeProps
    ? null
    : (props as ChoiceResultRenderProps)
  const [isRetrying, setIsRetrying] = useState(false)
  const [hasRetryError, setHasRetryError] = useState(false)
  const activityQuery = useQuery({
    queryKey: [
      'learning',
      'choice-activity',
      ...(routeProps ? routeIdentity(routeProps) : []),
    ],
    enabled: routeMode,
    queryFn: async () => {
      if (!routeProps) throw new Error('Missing route IDs')
      const result = await getChoiceActivityAction({
        data: {
          goalId: routeProps.goalId,
          skillId: routeProps.skillId,
          competencyId: routeProps.competencyId,
          activityId: routeProps.activityId,
        },
      })
      if (isActionFailure(result)) throw mapFailure(result)
      return result
    },
    retry: false,
    refetchOnWindowFocus: true,
  })
  const attemptQuery = useQuery({
    queryKey: [
      'learning',
      'choice-attempt',
      ...(routeProps ? [...routeIdentity(routeProps), routeProps.attemptId] : []),
    ],
    enabled: routeMode,
    queryFn: async () => {
      if (!routeProps) throw new Error('Missing route IDs')
      const result = await getChoiceAttemptAction({
        data: routeIdsForAttempt(routeProps),
      })
      if (isActionFailure(result)) throw mapFailure(result)
      return result
    },
    retry: false,
    refetchOnWindowFocus: (query) => query.state.data?.status === 'pending',
    refetchInterval: (query) => (query.state.data?.status === 'pending' ? 3000 : false),
    refetchIntervalInBackground: false,
  })

  useEffect(() => {
    if (!routeMode) return
    function refreshWhenVisible() {
      if (
        document.visibilityState === 'visible' &&
        attemptQuery.data?.status === 'pending'
      ) {
        void attemptQuery.refetch()
      }
    }
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => document.removeEventListener('visibilitychange', refreshWhenVisible)
  }, [attemptQuery.data?.status, attemptQuery.refetch, routeMode])

  const routeError = activityQuery.error ?? attemptQuery.error
  const isPrivateAbsence =
    routeError instanceof RestError && routeError.statusCode === 404
  const isSessionRejected = routeError instanceof AuthError
  useEffect(() => {
    if (isSessionRejected) routeProps?.onSessionExpired()
  }, [isSessionRejected, routeProps?.onSessionExpired])

  const legacyAttempt = legacyProps?.state === 'result' ? legacyProps.attempt : null
  const legacyActivity = legacyProps?.state === 'result' ? legacyProps.activity : null
  const attempt = routeMode ? (attemptQuery.data ?? null) : legacyAttempt
  const activity = routeMode ? (activityQuery.data ?? null) : legacyActivity
  const canRetry = Boolean(
    attempt?.status === 'failed' && attempt.retryAllowed && !isRetrying,
  )
  const resultState: ChoiceResultRenderProps['state'] = !routeProps
    ? (legacyProps?.state ?? 'loading')
    : isPrivateAbsence
      ? 'private-absence'
      : routeError && !isSessionRejected
        ? 'error'
        : activityQuery.isPending || attemptQuery.isPending || !activity || !attempt
          ? 'loading'
          : 'result'

  async function handleRetryEvaluation() {
    if (!canRetry || !attempt) return
    setIsRetrying(true)
    setHasRetryError(false)
    try {
      if (routeProps) {
        const result = await retryChoiceEvaluationAction({
          data: routeIdsForAttempt(routeProps),
        })
        if (isActionFailure(result)) throw mapFailure(result)
        await attemptQuery.refetch()
      } else if (legacyProps?.state === 'result') {
        await legacyProps.onRetryEvaluation()
      }
    } catch {
      setHasRetryError(true)
    } finally {
      setIsRetrying(false)
    }
  }

  const renderProps: ChoiceResultRenderProps = !routeProps
    ? (legacyProps ?? { state: 'loading' })
    : resultState === 'result' && activity && attempt
      ? {
          state: 'result',
          activity,
          attempt,
          recommendation: attempt.nextAction,
          onRetryEvaluation: handleRetryEvaluation,
          onReturnToActivity: routeProps?.onNavigateToActivity,
          onOpenRecommendation: routeProps?.onOpenRecommendation,
        }
      : resultState === 'error'
        ? {
            state: 'error',
            onRetryLoad: () =>
              void Promise.all([activityQuery.refetch(), attemptQuery.refetch()]),
          }
        : resultState === 'private-absence'
          ? { state: 'private-absence' }
          : { state: 'loading' }

  return {
    attempt,
    canRetry,
    handleRetryEvaluation,
    handleRetryLoad: async () => {
      await Promise.all([activityQuery.refetch(), attemptQuery.refetch()])
    },
    hasRetryError,
    isRetrying,
    pageState: resultState,
    renderProps,
  }
}

export type ChoiceResultPageController = ReturnType<typeof useChoiceResultPage>

function isRoutePageProps(
  value: ChoiceResultPageProps | ChoiceResultRouteProps,
): value is ChoiceResultRouteProps {
  return 'attemptId' in value
}

function routeIdentity(props: ChoiceResultRouteProps) {
  return [props.goalId, props.skillId, props.competencyId, props.activityId]
}

function isRouteInput(value: unknown): value is ChoiceResultRouteIds {
  if (!isRecord(value)) return false
  return (
    isIdentifier(value.goalId) &&
    isIdentifier(value.skillId) &&
    isIdentifier(value.competencyId) &&
    isIdentifier(value.activityId) &&
    isIdentifier(value.attemptId)
  )
}

function routeIdsForAttempt(props: ChoiceResultRouteProps): ChoiceResultRouteIds {
  return {
    goalId: props.goalId,
    skillId: props.skillId,
    competencyId: props.competencyId,
    activityId: props.activityId,
    attemptId: props.attemptId,
  }
}

function isActionFailure(value: unknown): value is ActionFailure {
  return isRecord(value) && typeof value.kind === 'string'
}

function mapFailure(failure: ActionFailure): Error {
  if (failure.kind === 'unauthorized')
    return new AuthError('authentication-rejected', 'Sua sessão expirou.', {
      statusCode: 401,
    })
  if (failure.kind === 'not-found') return new RestError('Resultado não encontrado.', 404)
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

function isIdentifier(value: unknown): value is string {
  return typeof value === 'string' && COMPETENCY_DETAIL_ID_PATTERN.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
