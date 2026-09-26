import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { RestError } from '@/core/errors/rest-error'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import type { SkillExperienceDetail } from '@/core/learning/skill-experience'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'

export type SkillExperienceInput = { goalId: string; skillId: string }

type ActionFailure = { kind: 'unauthorized' | 'not-found' | 'unavailable' }

type RetryInput = SkillExperienceInput & {
  activityId: string
  attemptId: string
  competencyId: string
}

function learningService() {
  return LearningService(
    AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
  )
}

export const getSkillExperienceAction = createServerFn({ method: 'GET' })
  .validator((input: SkillExperienceInput) => input)
  .handler(async ({ data }): Promise<SkillExperienceDetail | ActionFailure> => {
    if (
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.goalId) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(data.skillId)
    )
      return { kind: 'not-found' }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await learningService().getSkillExperienceDetail(
        access.accessToken,
        data.goalId,
        data.skillId,
      )
    } catch (error) {
      if (error instanceof RestError && error.statusCode === 401)
        return { kind: 'unauthorized' }
      if (error instanceof RestError && error.statusCode === 404)
        return { kind: 'not-found' }
      return { kind: 'unavailable' }
    }
  })

export const retrySkillEvaluationAction = createServerFn({ method: 'POST' })
  .validator((input: RetryInput) => input)
  .handler(async ({ data }): Promise<{ ok: true } | ActionFailure> => {
    if (!Object.values(data).every((id) => COMPETENCY_DETAIL_ID_PATTERN.test(id)))
      return { kind: 'not-found' }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      await learningService().retryChoiceEvaluation(access.accessToken, data)
      return { ok: true }
    } catch (error) {
      if (error instanceof RestError && error.statusCode === 401)
        return { kind: 'unauthorized' }
      if (error instanceof RestError && error.statusCode === 404)
        return { kind: 'not-found' }
      return { kind: 'unavailable' }
    }
  })

export function useSkillExperience(props: SkillExperienceInput) {
  const [isRetrying, setIsRetrying] = useState(false)
  const [retryFailed, setRetryFailed] = useState(false)

  const experienceQuery = useQuery({
    queryKey: ['learning', 'skill-experience', props.goalId, props.skillId],
    queryFn: async () => {
      const result = await getSkillExperienceAction({ data: props })
      if ('kind' in result)
        throw new RestError(
          'Habilidade indisponível.',
          result.kind === 'not-found' ? 404 : result.kind === 'unauthorized' ? 401 : 503,
        )
      return result
    },
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.evaluation?.status === 'pending' ? 3000 : false,
  })

  async function handleRetryEvaluation() {
    const evaluation = experienceQuery.data?.evaluation
    if (isRetrying || evaluation?.status !== 'failed') return
    setIsRetrying(true)
    setRetryFailed(false)
    const result = await retrySkillEvaluationAction({
      data: {
        activityId: evaluation.activityId,
        attemptId: evaluation.attemptId,
        competencyId: evaluation.competencyId,
        goalId: props.goalId,
        skillId: props.skillId,
      },
    })
    setIsRetrying(false)
    if ('kind' in result) {
      setRetryFailed(true)
      return
    }
    await experienceQuery.refetch()
  }

  return {
    experience: experienceQuery.data ?? null,
    handleRetryEvaluation,
    isExperienceLoading: experienceQuery.isPending,
    isRetrying,
    retryFailed,
  }
}
