import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { PracticeDraft } from '@/core/learning/choice-activity'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import { PRACTICE_PHOTO_KEY_PATTERN } from '@/core/learning/practice-photo-rules'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'
import { serverFunctionTelemetryMiddleware } from '@/start'

export type PracticeDraftIds = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
}

export type PracticeDraftFailure =
  | { kind: 'invalid-request' }
  | { kind: 'unauthorized' }
  | { kind: 'not-found' }
  | { kind: 'draft-closed' }
  | { kind: 'evaluation-pending' }
  | { kind: 'unavailable' }

type InvalidRequest = { kind: 'invalid-request' }
type SaveReflectionInput = { ids: PracticeDraftIds; reflection: string }
type RemovePhotoInput = { ids: PracticeDraftIds; recordKey: string }

export function isPracticeDraftFailure(value: unknown): value is PracticeDraftFailure {
  return typeof value === 'object' && value !== null && 'kind' in value
}

export const getPracticeDraftAction = createServerFn({ method: 'GET' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((input: unknown): PracticeDraftIds | InvalidRequest =>
    isDraftIds(input) ? pickIds(input) : { kind: 'invalid-request' },
  )
  .handler(
    async ({
      data,
      context,
    }: {
      data: PracticeDraftIds | InvalidRequest
      context: RequestTelemetryContext
    }): Promise<PracticeDraft | PracticeDraftFailure> => {
      if ('kind' in data) return data
      try {
        const { accessToken, service } = await getScopedService(context)
        return await service.getPracticeDraft(accessToken, data)
      } catch (error) {
        return toFailure(error)
      }
    },
  )

export const savePracticeReflectionAction = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((input: unknown): SaveReflectionInput | InvalidRequest =>
    isRecord(input) && isDraftIds(input.ids) && typeof input.reflection === 'string'
      ? { ids: pickIds(input.ids), reflection: input.reflection }
      : { kind: 'invalid-request' },
  )
  .handler(
    async ({
      data,
      context,
    }: {
      data: SaveReflectionInput | InvalidRequest
      context: RequestTelemetryContext
    }): Promise<PracticeDraft | PracticeDraftFailure> => {
      if ('kind' in data) return data
      try {
        const { accessToken, service } = await getScopedService(context)
        return await service.savePracticeReflection(
          accessToken,
          data.ids,
          data.reflection,
        )
      } catch (error) {
        return toFailure(error)
      }
    },
  )

export const removePracticePhotoAction = createServerFn({ method: 'POST' })
  .middleware([serverFunctionTelemetryMiddleware])
  .validator((input: unknown): RemovePhotoInput | InvalidRequest =>
    isRecord(input) &&
    isDraftIds(input.ids) &&
    typeof input.recordKey === 'string' &&
    PRACTICE_PHOTO_KEY_PATTERN.test(input.recordKey)
      ? { ids: pickIds(input.ids), recordKey: input.recordKey }
      : { kind: 'invalid-request' },
  )
  .handler(
    async ({
      data,
      context,
    }: {
      data: RemovePhotoInput | InvalidRequest
      context: RequestTelemetryContext
    }): Promise<PracticeDraft | PracticeDraftFailure> => {
      if ('kind' in data) return data
      try {
        const { accessToken, service } = await getScopedService(context)
        return await service.removePracticePhoto(accessToken, data.ids, data.recordKey)
      } catch (error) {
        return toFailure(error)
      }
    },
  )

async function getScopedService(context: RequestTelemetryContext) {
  const access = await getBetterAuthProvider().getCurrentAccess(
    getRequest(),
    context.requestId,
  )
  if (!access) throw new RestError('Sua sessão expirou.', HTTP_STATUS_CODE.unauthorized)
  return {
    accessToken: access.accessToken,
    service: LearningService(
      createServerRequestClient(context, { baseUrl: BetterAuthConfig().identityURL }),
    ),
  }
}

function toFailure(error: unknown): PracticeDraftFailure {
  if (error instanceof AuthError && error.kind !== 'unavailable')
    return { kind: 'unauthorized' }
  if (error instanceof RestError) {
    if (error.statusCode === HTTP_STATUS_CODE.unauthorized)
      return { kind: 'unauthorized' }
    if (error.statusCode === HTTP_STATUS_CODE.notFound) return { kind: 'not-found' }
    if (error.statusCode === HTTP_STATUS_CODE.conflict)
      return error.code === 'conflict'
        ? { kind: 'evaluation-pending' }
        : { kind: 'draft-closed' }
  }
  return { kind: 'unavailable' }
}

function pickIds(ids: PracticeDraftIds): PracticeDraftIds {
  return {
    goalId: ids.goalId,
    skillId: ids.skillId,
    competencyId: ids.competencyId,
    activityId: ids.activityId,
  }
}

function isDraftIds(value: unknown): value is PracticeDraftIds {
  return (
    isRecord(value) &&
    [value.goalId, value.skillId, value.competencyId, value.activityId].every(
      (id) => typeof id === 'string' && COMPETENCY_DETAIL_ID_PATTERN.test(id),
    )
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
