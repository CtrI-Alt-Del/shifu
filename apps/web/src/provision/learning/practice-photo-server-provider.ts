import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import {
  PRACTICE_PHOTO_ACCEPTED_MEDIA_TYPES,
  PRACTICE_PHOTO_KEY_PATTERN,
  PRACTICE_PHOTO_MAX_BODY_BYTES,
  PRACTICE_PHOTO_MAX_BYTES,
  PRACTICE_PHOTO_MEDIA_TYPES_BY_EXTENSION,
  getPracticePhotoExtension,
} from '@/core/learning/practice-photo-rules'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'

const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const RESPONSE_HEADERS = {
  'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff',
}
const CLIENT_CLOSED_REQUEST_STATUS_CODE = 499

type Failure = { code: string; message: string }

export type PracticeActivityIds = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
}

export const PracticePhotoServerProvider = () => {
  async function handlePracticePhotoUpload(
    request: Request,
    ids: PracticeActivityIds,
    recordKey: string,
    context?: RequestTelemetryContext,
  ): Promise<Response> {
    if (!hasValidIds(ids) || !PRACTICE_PHOTO_KEY_PATTERN.test(recordKey))
      return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
        code: 'malformed_photo',
        message: 'Não foi possível ler esta foto.',
      })
    if (!isSameOriginRequest(request))
      return jsonFailure(HTTP_STATUS_CODE.forbidden, {
        code: 'same_origin_required',
        message: 'Não foi possível enviar a foto.',
      })

    const contentLength = request.headers.get('content-length')
    if (contentLength !== null) {
      if (!/^\d+$/.test(contentLength))
        return jsonFailure(HTTP_STATUS_CODE.badRequest, {
          code: 'malformed_photo',
          message: 'Não foi possível ler esta foto.',
        })
      if (Number(contentLength) > PRACTICE_PHOTO_MAX_BODY_BYTES)
        return jsonFailure(HTTP_STATUS_CODE.payloadTooLarge, TOO_LARGE_FAILURE)
    }

    let body: Uint8Array
    try {
      body = await readBoundedBody(request, PRACTICE_PHOTO_MAX_BODY_BYTES)
    } catch {
      if (request.signal.aborted)
        return new Response(null, {
          status: CLIENT_CLOSED_REQUEST_STATUS_CODE,
          headers: RESPONSE_HEADERS,
        })
      return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
        code: 'malformed_photo',
        message: 'Não foi possível ler esta foto.',
      })
    }
    if (body.byteLength > PRACTICE_PHOTO_MAX_BODY_BYTES)
      return jsonFailure(HTTP_STATUS_CODE.payloadTooLarge, TOO_LARGE_FAILURE)

    let formData: FormData
    try {
      const headers = new Headers(request.headers)
      headers.delete('content-length')
      const arrayBuffer = new ArrayBuffer(body.byteLength)
      new Uint8Array(arrayBuffer).set(body)
      const boundedRequest = new Request(request.url, {
        method: 'POST',
        headers,
        body: new Blob([arrayBuffer]),
        signal: request.signal,
      })
      formData = await boundedRequest.formData()
    } catch {
      return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
        code: 'malformed_photo',
        message: 'Não foi possível ler esta foto.',
      })
    }

    const entries = [...formData.entries()]
    const file = formData.get('file')
    const uploadKey = formData.get('upload_key')
    if (
      entries.length !== 2 ||
      entries.some(([name]) => name !== 'file' && name !== 'upload_key') ||
      !(file instanceof File) ||
      typeof uploadKey !== 'string' ||
      !UUID_V4_PATTERN.test(uploadKey)
    )
      return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
        code: 'malformed_photo',
        message: 'Não foi possível ler esta foto.',
      })
    if (file.size > PRACTICE_PHOTO_MAX_BYTES)
      return jsonFailure(HTTP_STATUS_CODE.payloadTooLarge, TOO_LARGE_FAILURE)
    if (file.size === 0)
      return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
        code: 'malformed_photo',
        message: 'Não foi possível ler esta foto.',
      })

    const mediaType =
      PRACTICE_PHOTO_MEDIA_TYPES_BY_EXTENSION[getPracticePhotoExtension(file.name)]
    if (!mediaType)
      return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
        code: 'unsupported_photo',
        message: 'Use uma foto JPEG, PNG ou WebP.',
      })

    try {
      const { accessToken, service } = await getLearningScopedService(request, context)
      const normalizedFile =
        file.type.toLowerCase() === mediaType
          ? file
          : new File([file], file.name, { type: mediaType })
      const draft = await service.uploadPracticePhoto(
        accessToken,
        pickActivityIds(ids),
        { recordKey, uploadKey, file: normalizedFile },
        request.signal,
      )
      return new Response(JSON.stringify(draft), {
        status: HTTP_STATUS_CODE.ok,
        headers: { ...RESPONSE_HEADERS, 'Content-Type': 'application/json' },
      })
    } catch (error) {
      return photoFailureResponse(error)
    }
  }

  async function handlePracticeDraftPhotoRead(
    request: Request,
    ids: PracticeActivityIds,
    recordKey: string,
    context?: RequestTelemetryContext,
  ): Promise<Response> {
    if (!hasValidIds(ids) || !PRACTICE_PHOTO_KEY_PATTERN.test(recordKey))
      return jsonFailure(HTTP_STATUS_CODE.notFound, PHOTO_NOT_FOUND_FAILURE)

    try {
      const { accessToken, service } = await getLearningScopedService(request, context)
      const result = await service.readPracticePhotoContent(
        accessToken,
        pickActivityIds(ids),
        recordKey,
        request.signal,
      )
      return photoContentResponse(result)
    } catch (error) {
      return photoFailureResponse(error)
    }
  }

  async function handleAttemptPracticePhotoRead(
    request: Request,
    ids: PracticeActivityIds & { attemptId: string },
    photoId: string,
    context?: RequestTelemetryContext,
  ): Promise<Response> {
    if (
      !hasValidIds(ids) ||
      !COMPETENCY_DETAIL_ID_PATTERN.test(ids.attemptId) ||
      !PRACTICE_PHOTO_KEY_PATTERN.test(photoId)
    )
      return jsonFailure(HTTP_STATUS_CODE.notFound, PHOTO_NOT_FOUND_FAILURE)

    try {
      const { accessToken, service } = await getLearningScopedService(request, context)
      const result = await service.readAttemptPracticePhotoContent(
        accessToken,
        { ...pickActivityIds(ids), attemptId: ids.attemptId },
        photoId,
        request.signal,
      )
      return photoContentResponse(result)
    } catch (error) {
      return photoFailureResponse(error)
    }
  }

  async function getLearningScopedService(
    request: Request,
    context?: RequestTelemetryContext,
  ) {
    const access = context
      ? await getBetterAuthProvider().getCurrentAccess(request, context.requestId)
      : await getBetterAuthProvider().getCurrentAccess(request)
    if (!access)
      throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
    return {
      accessToken: access.accessToken,
      service: LearningService(
        createServerRequestClient(context, { baseUrl: BetterAuthConfig().identityURL }),
      ),
    }
  }

  function pickActivityIds(ids: PracticeActivityIds): PracticeActivityIds {
    return {
      goalId: ids.goalId,
      skillId: ids.skillId,
      competencyId: ids.competencyId,
      activityId: ids.activityId,
    }
  }

  function hasValidIds(ids: PracticeActivityIds): boolean {
    return [ids.goalId, ids.skillId, ids.competencyId, ids.activityId].every((id) =>
      COMPETENCY_DETAIL_ID_PATTERN.test(id),
    )
  }

  function photoContentResponse(result: {
    body: Blob
    headers: Record<string, string>
    statusCode: number
  }): Response {
    const mediaType = result.headers['content-type']
      ?.split(';', 1)[0]
      ?.trim()
      .toLowerCase()
    if (!mediaType || !PRACTICE_PHOTO_ACCEPTED_MEDIA_TYPES.includes(mediaType))
      return jsonFailure(HTTP_STATUS_CODE.serviceUnavailable, UNAVAILABLE_FAILURE)
    return new Response(result.body, {
      status: result.statusCode,
      headers: {
        ...RESPONSE_HEADERS,
        'Content-Type': mediaType,
        'Content-Disposition': 'inline',
      },
    })
  }

  function isSameOriginRequest(request: Request): boolean {
    const origin = request.headers.get('origin')
    if (!origin) return false
    try {
      return new URL(origin).origin === new URL(request.url).origin
    } catch {
      return false
    }
  }

  async function readBoundedBody(
    request: Request,
    maximumBytes: number,
  ): Promise<Uint8Array> {
    if (!request.body) return new Uint8Array()
    const reader = request.body.getReader()
    const chunks: Uint8Array[] = []
    let byteLength = 0
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        byteLength += value.byteLength
        if (byteLength > maximumBytes) {
          await reader.cancel()
          return new Uint8Array(maximumBytes + 1)
        }
        chunks.push(value)
      }
    } finally {
      reader.releaseLock()
    }
    const body = new Uint8Array(byteLength)
    let offset = 0
    for (const chunk of chunks) {
      body.set(chunk, offset)
      offset += chunk.byteLength
    }
    return body
  }

  function photoFailureResponse(error: unknown): Response {
    const statusCode =
      error instanceof RestError
        ? allowedFailureStatus(error.statusCode)
        : error instanceof AppError && error.title === 'Erro de autenticação'
          ? HTTP_STATUS_CODE.unauthorized
          : HTTP_STATUS_CODE.serviceUnavailable
    const code = error instanceof RestError ? error.code : undefined
    return jsonFailure(statusCode, failureFor(statusCode, code))
  }

  function allowedFailureStatus(statusCode: number): number {
    const allowed = new Set<number>([
      HTTP_STATUS_CODE.unauthorized,
      HTTP_STATUS_CODE.forbidden,
      HTTP_STATUS_CODE.notFound,
      HTTP_STATUS_CODE.conflict,
      HTTP_STATUS_CODE.payloadTooLarge,
      HTTP_STATUS_CODE.unprocessableEntity,
    ])
    return allowed.has(statusCode) ? statusCode : HTTP_STATUS_CODE.serviceUnavailable
  }

  function failureFor(statusCode: number, code: string | undefined): Failure {
    if (statusCode === HTTP_STATUS_CODE.conflict) {
      if (code === 'practice_draft_closed' || code === 'practice_draft_conflict')
        return DRAFT_CLOSED_FAILURE
      if (code?.includes('upload_key'))
        return {
          code: 'upload_key_conflict',
          message: 'Não foi possível reutilizar este envio. Tente novamente.',
        }
      if (code === 'conflict') return EVALUATION_PENDING_FAILURE
      return UNAVAILABLE_FAILURE_WITH_CONFLICT
    }
    if (statusCode === HTTP_STATUS_CODE.unprocessableEntity)
      return code === 'malformed_photo'
        ? {
            code,
            message:
              'Não foi possível ler esta foto. Use uma foto JPEG, PNG ou WebP válida.',
          }
        : UNSUPPORTED_FAILURE
    return failureForStatus(statusCode)
  }

  function failureForStatus(statusCode: number): Failure {
    const failures: Record<number, Failure> = {
      [HTTP_STATUS_CODE.unauthorized]: {
        code: 'unauthenticated',
        message: 'Sua sessão expirou. Atualize a página.',
      },
      [HTTP_STATUS_CODE.forbidden]: {
        code: 'inactive_account',
        message: 'Sua conta não pode acessar esta foto.',
      },
      [HTTP_STATUS_CODE.notFound]: PHOTO_NOT_FOUND_FAILURE,
      [HTTP_STATUS_CODE.conflict]: DRAFT_CLOSED_FAILURE,
      [HTTP_STATUS_CODE.payloadTooLarge]: TOO_LARGE_FAILURE,
      [HTTP_STATUS_CODE.unprocessableEntity]: UNSUPPORTED_FAILURE,
    }
    return failures[statusCode] ?? UNAVAILABLE_FAILURE
  }

  function jsonFailure(statusCode: number, failure: Failure): Response {
    return new Response(JSON.stringify(failure), {
      status: statusCode,
      headers: { ...RESPONSE_HEADERS, 'Content-Type': 'application/json' },
    })
  }

  return {
    handlePracticePhotoUpload,
    handlePracticeDraftPhotoRead,
    handleAttemptPracticePhotoRead,
  }
}

const TOO_LARGE_FAILURE: Failure = {
  code: 'photo_too_large',
  message: 'A foto excede o limite de 10 MB.',
}
const PHOTO_NOT_FOUND_FAILURE: Failure = {
  code: 'photo_not_found',
  message: 'Esta foto não está disponível.',
}
const UNAVAILABLE_FAILURE: Failure = {
  code: 'photo_unavailable',
  message: 'Não foi possível concluir agora. Tente novamente.',
}

const DRAFT_CLOSED_FAILURE: Failure = {
  code: 'practice_draft_closed',
  message: 'Este rascunho foi encerrado. Recarregue a página.',
}
const EVALUATION_PENDING_FAILURE: Failure = {
  code: 'conflict',
  message: 'Há uma avaliação pendente nesta Habilidade.',
}
const UNSUPPORTED_FAILURE: Failure = {
  code: 'unsupported_photo',
  message: 'Use uma foto JPEG, PNG ou WebP válida.',
}
const UNAVAILABLE_FAILURE_WITH_CONFLICT: Failure = {
  code: 'photo_conflict',
  message: 'Não foi possível concluir agora. Tente novamente.',
}
