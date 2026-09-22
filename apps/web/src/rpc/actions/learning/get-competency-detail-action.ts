import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import {
  LearningService,
  type CompetencyDetailResponse,
} from '@/rest/services/learning-service'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'

export type GetCompetencyDetailActionFailure =
  | { kind: 'invalid-request' }
  | { kind: 'unauthorized' }
  | { kind: 'not-found' }
  | { kind: 'unavailable'; statusCode?: number }

export type GetCompetencyDetailActionResult =
  | CompetencyDetailResponse
  | GetCompetencyDetailActionFailure

type GetCompetencyDetailActionInput = {
  goalId: string
  skillId: string
  competencyId: string
}

type ValidatedActionInput = GetCompetencyDetailActionInput | { kind: 'invalid-request' }

export const getCompetencyDetailAction = createServerFn({ method: 'GET' })
  .validator((input: unknown): ValidatedActionInput => {
    if (!isRecord(input)) return { kind: 'invalid-request' }

    if (
      !isIdentifier(input.goalId) ||
      !isIdentifier(input.skillId) ||
      !isIdentifier(input.competencyId)
    ) {
      return { kind: 'invalid-request' }
    }

    return {
      goalId: input.goalId,
      skillId: input.skillId,
      competencyId: input.competencyId,
    }
  })
  .handler(async ({ data }): Promise<GetCompetencyDetailActionResult> => {
    if ('kind' in data) return data

    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const service = LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      )

      return await service.getCompetencyDetail(
        access.accessToken,
        data.goalId,
        data.skillId,
        data.competencyId,
      )
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

function isIdentifier(value: unknown): value is string {
  return typeof value === 'string' && COMPETENCY_DETAIL_ID_PATTERN.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
