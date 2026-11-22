import { Blob as NodeBlob, File as NodeFile } from 'node:buffer'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { RestResponse } from '@/core/shared/responses/rest-response'

const ports = vi.hoisted(() => ({
  getCurrentAccess: vi.fn(),
  uploadPracticePhoto: vi.fn(),
  readPracticePhotoContent: vi.fn(),
  readAttemptPracticePhotoContent: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: unknown) => ({ options }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: ports.getCurrentAccess }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-config', () => ({
  BetterAuthConfig: () => ({ identityURL: 'http://shifu.test' }),
}))
vi.mock('@/rest/axios/server-request-client', () => ({
  createServerRequestClient: () => ({}),
}))
vi.mock('@/rest/services/learning-service', () => ({
  LearningService: () => ({
    uploadPracticePhoto: ports.uploadPracticePhoto,
    readPracticePhotoContent: ports.readPracticePhotoContent,
    readAttemptPracticePhotoContent: ports.readAttemptPracticePhotoContent,
  }),
}))

import { Route as attemptPhotoRoute } from '@/routes/api/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId/practice-photos/$photoId'
import { Route as draftPhotoRoute } from '@/routes/api/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/practice-photos/$recordKey'

const IDS = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  competencyId: '01J00000000000000000000003',
  activityId: '01J00000000000000000000004',
}
const ATTEMPT_ID = '01J00000000000000000000005'
const UPLOAD_KEY = 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259'
const BASE_URL = 'http://localhost:7000'
const MAX_PHOTO_BYTES = 10 * 1024 * 1024
const DRAFT_PHOTO_URL = `${BASE_URL}/api/learning/goals/${IDS.goalId}/skills/${IDS.skillId}/competencies/${IDS.competencyId}/activities/${IDS.activityId}/practice-photos/cuts`
const TELEMETRY_CONTEXT = {
  requestId: '11111111-1111-4111-8111-111111111111',
  telemetry: { emit: vi.fn() },
} satisfies RequestTelemetryContext

type HandlerContext = {
  request: Request
  params: Record<string, string>
  context: RequestTelemetryContext
}
type RouteWithHandlers = {
  options: {
    server?: { handlers?: Record<string, (context: HandlerContext) => Promise<Response>> }
  }
}

function handler(route: unknown, method: string) {
  const registered = (route as RouteWithHandlers).options.server?.handlers?.[method]
  if (!registered) throw new Error(`The route must register a ${method} handler.`)
  return registered
}

function joinBytes(chunks: Uint8Array[]): Uint8Array {
  const result = new Uint8Array(
    chunks.reduce((size, chunk) => size + chunk.byteLength, 0),
  )
  let offset = 0
  for (const chunk of chunks) {
    result.set(chunk, offset)
    offset += chunk.byteLength
  }
  return result
}

function uploadRequest(
  options: {
    uploadKey?: string
    filename?: string
    mediaType?: string
    contents?: Uint8Array
    origin?: string | null
    extraField?: boolean
    contentLength?: string
  } = {},
): Request {
  const boundary = 'shifu-practice-photo-test-boundary'
  const encoder = new TextEncoder()
  const chunks = [
    encoder.encode(
      `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${options.filename ?? 'cortes.jpg'}"\r\nContent-Type: ${options.mediaType ?? 'image/jpeg'}\r\n\r\n`,
    ),
    options.contents ?? new Uint8Array([1, 2, 3]),
    encoder.encode(
      `\r\n--${boundary}\r\nContent-Disposition: form-data; name="upload_key"\r\n\r\n${options.uploadKey ?? UPLOAD_KEY}\r\n`,
    ),
  ]
  if (options.extraField)
    chunks.push(
      encoder.encode(
        `--${boundary}\r\nContent-Disposition: form-data; name="unexpected"\r\n\r\nvalue\r\n`,
      ),
    )
  chunks.push(encoder.encode(`--${boundary}--\r\n`))
  const bytes = joinBytes(chunks)
  const body = new ArrayBuffer(bytes.byteLength)
  new Uint8Array(body).set(bytes)
  const headers = new Headers()
  headers.set('content-type', `multipart/form-data; boundary=${boundary}`)
  if (options.origin !== null) headers.set('origin', options.origin ?? BASE_URL)
  if (options.contentLength !== undefined)
    headers.set('content-length', options.contentLength)
  return new Request(DRAFT_PHOTO_URL, { method: 'PUT', headers, body })
}

function oversizedStreamRequest(): Request {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array(MAX_PHOTO_BYTES + 65_537))
      controller.close()
    },
  })
  return {
    url: DRAFT_PHOTO_URL,
    headers: new Headers({ origin: BASE_URL }),
    signal: new AbortController().signal,
    body,
  } as Request
}

async function putPhoto(
  request = uploadRequest(),
  params: Record<string, string> = { ...IDS, recordKey: 'cuts' },
) {
  return handler(
    draftPhotoRoute,
    'PUT',
  )({
    request,
    params,
    context: TELEMETRY_CONTEXT,
  })
}

async function getDraftPhoto(
  params: Record<string, string> = { ...IDS, recordKey: 'cuts' },
) {
  return handler(
    draftPhotoRoute,
    'GET',
  )({
    request: new Request(DRAFT_PHOTO_URL),
    params,
    context: TELEMETRY_CONTEXT,
  })
}

async function getAttemptPhoto(
  params: Record<string, string> = {
    ...IDS,
    attemptId: ATTEMPT_ID,
    photoId: 'photo-1',
  },
) {
  return handler(
    attemptPhotoRoute,
    'GET',
  )({
    request: new Request(`${BASE_URL}/api/attempt-photo`),
    params,
    context: TELEMETRY_CONTEXT,
  })
}

async function expectPrivateFailure(response: Response, status: number, code: string) {
  expect(response.status).toBe(status)
  expect(response.headers.get('cache-control')).toBe('private, no-store')
  expect(response.headers.get('x-content-type-options')).toBe('nosniff')
  expect(response.headers.get('content-type')).toContain('application/json')
  expect(await response.json()).toEqual(expect.objectContaining({ code }))
}

const SAVED_DRAFT = {
  revision: 5,
  reflection: '',
  photos: [
    {
      recordKey: 'cuts',
      photoId: 'photo-1',
      state: 'ready',
      mediaType: 'image/jpeg',
      sizeBytes: 3,
    },
  ],
}

describe('practice photo API route handlers', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.stubGlobal('Blob', NodeBlob)
    vi.stubGlobal('File', NodeFile)
    ports.getCurrentAccess.mockResolvedValue({ accessToken: 'private-access-token' })
    ports.uploadPracticePhoto.mockResolvedValue(SAVED_DRAFT)
  })
  afterEach(() => vi.unstubAllGlobals())

  describe('upload', () => {
    it('rejects malformed identifiers and cross-origin requests before authenticating', async () => {
      const malformed = await putPhoto(uploadRequest(), {
        ...IDS,
        activityId: 'invalid',
        recordKey: 'cuts',
      })
      const malformedRecord = await putPhoto(uploadRequest(), {
        ...IDS,
        recordKey: '../cuts',
      })
      const crossOrigin = await putPhoto(
        uploadRequest({ origin: 'https://attacker.example' }),
      )
      const missingOrigin = await putPhoto(uploadRequest({ origin: null }))

      await expectPrivateFailure(
        malformed,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_photo',
      )
      await expectPrivateFailure(
        malformedRecord,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_photo',
      )
      await expectPrivateFailure(
        crossOrigin,
        HTTP_STATUS_CODE.forbidden,
        'same_origin_required',
      )
      await expectPrivateFailure(
        missingOrigin,
        HTTP_STATUS_CODE.forbidden,
        'same_origin_required',
      )
      expect(ports.getCurrentAccess).not.toHaveBeenCalled()
    })

    it('rejects an invalid Content-Length and a body above 10 MB plus the multipart overhead', async () => {
      const malformedLength = await putPhoto(uploadRequest({ contentLength: 'unknown' }))
      const declaredTooLarge = await putPhoto(
        uploadRequest({ contentLength: '10551297' }),
      )
      const streamedTooLarge = await putPhoto(oversizedStreamRequest())

      await expectPrivateFailure(
        malformedLength,
        HTTP_STATUS_CODE.badRequest,
        'malformed_photo',
      )
      await expectPrivateFailure(
        declaredTooLarge,
        HTTP_STATUS_CODE.payloadTooLarge,
        'photo_too_large',
      )
      await expectPrivateFailure(
        streamedTooLarge,
        HTTP_STATUS_CODE.payloadTooLarge,
        'photo_too_large',
      )
      expect(ports.uploadPracticePhoto).not.toHaveBeenCalled()
    })

    it('accepts a photo of exactly 10 MB and rejects one byte more', async () => {
      const exact = await putPhoto(
        uploadRequest({ contents: new Uint8Array(MAX_PHOTO_BYTES) }),
      )
      const oneByteMore = await putPhoto(
        uploadRequest({ contents: new Uint8Array(MAX_PHOTO_BYTES + 1) }),
      )

      expect(exact.status).toBe(HTTP_STATUS_CODE.ok)
      await expectPrivateFailure(
        oneByteMore,
        HTTP_STATUS_CODE.payloadTooLarge,
        'photo_too_large',
      )
      expect(ports.uploadPracticePhoto).toHaveBeenCalledTimes(1)
    })

    it('rejects empty, extra-field, malformed-key and unsupported uploads without forwarding', async () => {
      const empty = await putPhoto(uploadRequest({ contents: new Uint8Array() }))
      const extra = await putPhoto(uploadRequest({ extraField: true }))
      const badKey = await putPhoto(uploadRequest({ uploadKey: 'not-a-uuid' }))
      const unsupported = await putPhoto(
        uploadRequest({ filename: 'nota.pdf', mediaType: 'application/pdf' }),
      )

      await expectPrivateFailure(
        empty,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_photo',
      )
      await expectPrivateFailure(
        extra,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_photo',
      )
      await expectPrivateFailure(
        badKey,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_photo',
      )
      await expectPrivateFailure(
        unsupported,
        HTTP_STATUS_CODE.unprocessableEntity,
        'unsupported_photo',
      )
      expect(ports.uploadPracticePhoto).not.toHaveBeenCalled()
    })

    it('forwards a valid photo with its real media type and returns the saved draft', async () => {
      const response = await putPhoto(
        uploadRequest({ filename: 'prato.PNG', mediaType: 'application/octet-stream' }),
      )

      expect(response.status).toBe(HTTP_STATUS_CODE.ok)
      expect(response.headers.get('cache-control')).toBe('private, no-store')
      expect(response.headers.get('x-content-type-options')).toBe('nosniff')
      expect(await response.json()).toEqual(SAVED_DRAFT)
      expect(ports.uploadPracticePhoto).toHaveBeenCalledWith(
        'private-access-token',
        IDS,
        {
          recordKey: 'cuts',
          uploadKey: UPLOAD_KEY,
          file: expect.objectContaining({ name: 'prato.PNG', type: 'image/png' }),
        },
        expect.anything(),
      )
    })

    it('answers 401 without a session and never forwards the file', async () => {
      ports.getCurrentAccess.mockResolvedValue(null)

      await expectPrivateFailure(
        await putPhoto(),
        HTTP_STATUS_CODE.unauthorized,
        'unauthenticated',
      )
      expect(ports.uploadPracticePhoto).not.toHaveBeenCalled()
    })

    it.each([
      [HTTP_STATUS_CODE.notFound, 'photo_not_found'],
      [HTTP_STATUS_CODE.conflict, 'photo_conflict'],
      [HTTP_STATUS_CODE.payloadTooLarge, 'photo_too_large'],
      [HTTP_STATUS_CODE.unprocessableEntity, 'unsupported_photo'],
      [HTTP_STATUS_CODE.forbidden, 'inactive_account'],
      [500, 'photo_unavailable'],
    ])('maps a %s service failure to the safe %s response', async (status, code) => {
      ports.uploadPracticePhoto.mockRejectedValue(new RestError('private detail', status))

      const expectedStatus = status === 500 ? HTTP_STATUS_CODE.serviceUnavailable : status
      await expectPrivateFailure(await putPhoto(), expectedStatus, code)
    })

    it.each([
      [HTTP_STATUS_CODE.conflict, 'practice_draft_closed', 'practice_draft_closed'],
      [HTTP_STATUS_CODE.conflict, 'conflict', 'conflict'],
      [HTTP_STATUS_CODE.conflict, 'upload_key_reused', 'upload_key_conflict'],
      [HTTP_STATUS_CODE.conflict, 'other', 'photo_conflict'],
      [HTTP_STATUS_CODE.unprocessableEntity, 'malformed_photo', 'malformed_photo'],
    ])('maps the server %s code %s to %s', async (status, serverCode, expectedCode) => {
      ports.uploadPracticePhoto.mockRejectedValue(
        new RestError('private', status, serverCode),
      )

      await expectPrivateFailure(await putPhoto(), status, expectedCode)
    })

    it('answers 503 for an unexpected failure without leaking details', async () => {
      ports.uploadPracticePhoto.mockRejectedValue(new Error('database password'))

      const response = await putPhoto()

      await expectPrivateFailure(
        response,
        HTTP_STATUS_CODE.serviceUnavailable,
        'photo_unavailable',
      )
    })

    it('answers 401 when the session helper reports an authentication failure', async () => {
      ports.getCurrentAccess.mockRejectedValue(
        new AppError('Sua sessão expirou.', 'Erro de autenticação'),
      )

      await expectPrivateFailure(
        await putPhoto(),
        HTTP_STATUS_CODE.unauthorized,
        'unauthenticated',
      )
    })
  })

  describe('reading photo bytes', () => {
    function photoResponse(contentType = 'image/webp') {
      return new RestResponse<Blob>({
        body: new NodeBlob(['bytes']) as unknown as Blob,
        statusCode: 200,
        headers: { 'content-type': `${contentType}; charset=binary` },
      })
    }

    it('streams a draft photo inline with private headers', async () => {
      ports.readPracticePhotoContent.mockResolvedValue(photoResponse())

      const response = await getDraftPhoto()

      expect(response.status).toBe(HTTP_STATUS_CODE.ok)
      expect(response.headers.get('content-type')).toBe('image/webp')
      expect(response.headers.get('content-disposition')).toBe('inline')
      expect(response.headers.get('cache-control')).toBe('private, no-store')
      expect(response.headers.get('x-content-type-options')).toBe('nosniff')
      expect(ports.readPracticePhotoContent).toHaveBeenCalledWith(
        'private-access-token',
        IDS,
        'cuts',
        expect.anything(),
      )
    })

    it('streams an attempt photo through the attempt route', async () => {
      ports.readAttemptPracticePhotoContent.mockResolvedValue(photoResponse('image/png'))

      const response = await getAttemptPhoto()

      expect(response.status).toBe(HTTP_STATUS_CODE.ok)
      expect(response.headers.get('content-type')).toBe('image/png')
      expect(ports.readAttemptPracticePhotoContent).toHaveBeenCalledWith(
        'private-access-token',
        { ...IDS, attemptId: ATTEMPT_ID },
        'photo-1',
        expect.anything(),
      )
    })

    it('treats malformed identifiers as not found without calling the service', async () => {
      await expectPrivateFailure(
        await getDraftPhoto({ ...IDS, recordKey: '../x' }),
        HTTP_STATUS_CODE.notFound,
        'photo_not_found',
      )
      await expectPrivateFailure(
        await getAttemptPhoto({ ...IDS, attemptId: 'bad', photoId: 'photo-1' }),
        HTTP_STATUS_CODE.notFound,
        'photo_not_found',
      )
      expect(ports.getCurrentAccess).not.toHaveBeenCalled()
    })

    it('does not serve a body whose media type is not an accepted image', async () => {
      ports.readPracticePhotoContent.mockResolvedValue(photoResponse('text/html'))

      await expectPrivateFailure(
        await getDraftPhoto(),
        HTTP_STATUS_CODE.serviceUnavailable,
        'photo_unavailable',
      )
    })

    it('answers 401 without a session and 404 for another learner photo', async () => {
      ports.getCurrentAccess.mockResolvedValueOnce(null)
      await expectPrivateFailure(
        await getDraftPhoto(),
        HTTP_STATUS_CODE.unauthorized,
        'unauthenticated',
      )

      ports.readAttemptPracticePhotoContent.mockRejectedValue(
        new RestError('not yours', HTTP_STATUS_CODE.notFound),
      )
      await expectPrivateFailure(
        await getAttemptPhoto(),
        HTTP_STATUS_CODE.notFound,
        'photo_not_found',
      )
    })
  })
})
