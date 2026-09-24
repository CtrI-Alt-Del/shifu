import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { GOAL_DETAIL_ID_PATTERN, type GoalDetail } from '@/core/learning/goal-detail'
import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { GoalDetailProvider } from '@/provision/learning/goal-detail-provider'

export type GoalDetailResult =
  | { kind: 'success'; detail: GoalDetail }
  | {
      kind: 'unauthorized' | 'forbidden' | 'not-found' | 'invalid-request' | 'unavailable'
      statusCode?: number
    }

type ValidatedInput = { goalId: string } | { kind: 'invalid-request' }

export const getGoalDetail = createServerFn({ method: 'GET' })
  .validator((input: unknown): ValidatedInput => {
    if (!isRecord(input) || !isGoalId(input.goalId)) return { kind: 'invalid-request' }

    return { goalId: input.goalId }
  })
  .handler(async ({ data }): Promise<GoalDetailResult> => {
    if ('kind' in data) return data

    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }

      const detail = await GoalDetailProvider().getGoalDetail(
        access.accessToken,
        data.goalId,
      )
      return { kind: 'success', detail }
    } catch (error) {
      if (error instanceof AuthError) {
        return error.kind === 'authentication-rejected'
          ? { kind: 'unauthorized', statusCode: error.statusCode }
          : { kind: 'unavailable', statusCode: error.statusCode }
      }

      if (error instanceof RestError) {
        if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
          return { kind: 'unauthorized' }
        if (error.statusCode === HTTP_STATUS_CODE.forbidden) return { kind: 'forbidden' }
        if (error.statusCode === HTTP_STATUS_CODE.notFound) return { kind: 'not-found' }
        if (error.statusCode === HTTP_STATUS_CODE.unprocessableEntity) {
          return { kind: 'invalid-request' }
        }
        return { kind: 'unavailable', statusCode: error.statusCode }
      }

      return { kind: 'unavailable' }
    }
  })

function isGoalId(value: unknown): value is string {
  return typeof value === 'string' && GOAL_DETAIL_ID_PATTERN.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
