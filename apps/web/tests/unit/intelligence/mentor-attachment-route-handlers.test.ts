import { Blob as NodeBlob, File as NodeFile } from 'node:buffer'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'
import type { RestClient } from '@/core/shared/interfaces/rest-client'
import type { RequestTelemetryContext } from '@/core/shared/interfaces/request-telemetry-context'
import { RestResponse } from '@/core/shared/responses/rest-response'
import { IntelligenceService } from '@/rest/services/intelligence-service'

const ports = vi.hoisted(() => ({
  getMentorScopedService: vi.fn(),
  uploadMentorAttachment: vi.fn(),
  readMentorAttachmentFile: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: unknown) => ({ options }),
}))
vi.mock('@/provision/realtime/mentor-response-stream-server-provider', () => ({
  getMentorScopedService: ports.getMentorScopedService,
}))

import { Route as uploadRoute } from '@/routes/api/intelligence/mentor-attachment-batches/$batchId/attachments'
import { Route as fileRoute } from '@/routes/api/intelligence/mentor-sessions/$sessionId/attachments/$attachmentId/file'

const BATCH_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
const ATTACHMENT_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0D'
const UPLOAD_KEY = 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259'
const BASE_URL = 'http://localhost:7000'

const TELEMETRY_CONTEXT = {
  requestId: '11111111-1111-4111-8111-111111111111',
  telemetry: { emit: vi.fn() },
} satisfies RequestTelemetryContext

type UploadHandlerContext = {
  request: Request
  params: { batchId: string }
  context: RequestTelemetryContext
}
type FileHandlerContext = {
  request: Request
  params: { sessionId: string; attachmentId: string }
  context: RequestTelemetryContext
}
type RouteWithHandlers<Handlers> = {
  options: { server?: { handlers?: Handlers } }
}

class CapturedFormData {
  private readonly fields: Array<[string, unknown, string | undefined]> = []

  append(name: string, value: unknown, filename?: string) {
    this.fields.push([name, value, filename])
  }

  get(name: string) {
    return this.fields.find(([fieldName]) => fieldName === name)?.[1] ?? null
  }
}

const uploadMentorAttachment = ports.uploadMentorAttachment
const readMentorAttachmentFile = ports.readMentorAttachmentFile
const scopedService = { uploadMentorAttachment, readMentorAttachmentFile }

function registeredUploadHandler() {
  const route = uploadRoute as unknown as RouteWithHandlers<{
    POST?: (context: UploadHandlerContext) => Promise<Response>
  }>
  const handler = route.options.server?.handlers?.POST
  if (!handler) throw new Error('The upload route must register a POST handler.')
  return handler
}

function registeredFileHandler() {
  const route = fileRoute as unknown as RouteWithHandlers<{
    GET?: (context: FileHandlerContext) => Promise<Response>
  }>
  const handler = route.options.server?.handlers?.GET
  if (!handler) throw new Error('The file route must register a GET handler.')
  return handler
}

function toBytes(value: string | Uint8Array): Uint8Array {
  return typeof value === 'string' ? new TextEncoder().encode(value) : value
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
    contents?: string | Uint8Array
    origin?: string | null
    extraField?: boolean
    contentLength?: string
  } = {},
): Request {
  const boundary = 'shifu-mentor-attachment-test-boundary'
  const chunks = [
    new TextEncoder().encode(
      `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="${options.filename ?? 'anotacao.txt'}"\r\nContent-Type: ${options.mediaType ?? 'text/plain'}\r\n\r\n`,
    ),
    toBytes(options.contents ?? 'anotação'),
    new TextEncoder().encode(
      `\r\n--${boundary}\r\nContent-Disposition: form-data; name="upload_key"\r\n\r\n${options.uploadKey ?? UPLOAD_KEY}\r\n`,
    ),
  ]
  if (options.extraField)
    chunks.push(
      new TextEncoder().encode(
        `--${boundary}\r\nContent-Disposition: form-data; name="unexpected"\r\n\r\nvalue\r\n`,
      ),
    )
  chunks.push(new TextEncoder().encode(`--${boundary}--\r\n`))
  const bytes = joinBytes(chunks)
  const body = new ArrayBuffer(bytes.byteLength)
  new Uint8Array(body).set(bytes)
  const headers = new Headers()
  headers.set('content-type', `multipart/form-data; boundary=${boundary}`)
  if (options.origin !== null) headers.set('origin', options.origin ?? BASE_URL)
  if (options.contentLength !== undefined)
    headers.set('content-length', options.contentLength)
  return new Request(
    `${BASE_URL}/api/intelligence/mentor-attachment-batches/${BATCH_ID}/attachments`,
    { method: 'POST', headers, body },
  )
}

function bodyLimitRequest(): Request {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array(10_065_537))
      controller.close()
    },
  })
  return {
    url: `${BASE_URL}/api/intelligence/mentor-attachment-batches/${BATCH_ID}/attachments`,
    headers: new Headers({ origin: BASE_URL }),
    signal: new AbortController().signal,
    body,
  } as Request
}

function fileRequest(preview?: string): Request {
  const url = new URL(
    `/api/intelligence/mentor-sessions/${SESSION_ID}/attachments/${ATTACHMENT_ID}/file`,
    BASE_URL,
  )
  if (preview !== undefined) url.searchParams.set('preview', preview)
  return new Request(url)
}

async function postUpload(request = uploadRequest(), batchId = BATCH_ID) {
  return registeredUploadHandler()({
    request,
    params: { batchId },
    context: TELEMETRY_CONTEXT,
  })
}

async function getFile(
  request = fileRequest(),
  sessionId = SESSION_ID,
  attachmentId = ATTACHMENT_ID,
) {
  return registeredFileHandler()({
    request,
    params: { sessionId, attachmentId },
    context: TELEMETRY_CONTEXT,
  })
}

async function expectPrivateFailure(response: Response, status: number, code: string) {
  expect(response.status).toBe(status)
  expect(response.headers.get('cache-control')).toBe('private, no-store')
  expect(response.headers.get('x-content-type-options')).toBe('nosniff')
  expect(response.headers.get('content-type')).toContain('application/json')
  const body = await response.json()
  expect(body).toEqual(expect.objectContaining({ code }))
  return body
}

describe('Mentor attachment API route handlers', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.stubGlobal('Blob', NodeBlob)
    vi.stubGlobal('File', NodeFile)
    ports.getMentorScopedService.mockResolvedValue({
      accessToken: 'private-access-token',
      service: scopedService,
    })
  })
  afterEach(() => vi.unstubAllGlobals())

  describe('upload', () => {
    it('rejects malformed batch identifiers and cross-origin requests before auth', async () => {
      const malformed = await postUpload(uploadRequest(), 'invalid')
      const crossOrigin = await postUpload(
        uploadRequest({ origin: 'https://attacker.example' }),
      )

      await expectPrivateFailure(
        malformed,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_attachment',
      )
      await expectPrivateFailure(
        crossOrigin,
        HTTP_STATUS_CODE.forbidden,
        'same_origin_required',
      )
      expect(ports.getMentorScopedService).not.toHaveBeenCalled()
    })

    it('rejects missing or malformed Origin and invalid Content-Length values', async () => {
      const missingOrigin = await postUpload(uploadRequest({ origin: null }))
      const malformedOrigin = await postUpload(uploadRequest({ origin: 'not an origin' }))
      const malformedLength = await postUpload(
        uploadRequest({ contentLength: 'unknown' }),
      )

      await expectPrivateFailure(
        missingOrigin,
        HTTP_STATUS_CODE.forbidden,
        'same_origin_required',
      )
      await expectPrivateFailure(
        malformedOrigin,
        HTTP_STATUS_CODE.forbidden,
        'same_origin_required',
      )
      await expectPrivateFailure(
        malformedLength,
        HTTP_STATUS_CODE.badRequest,
        'malformed_attachment',
      )
      expect(ports.getMentorScopedService).not.toHaveBeenCalled()
    })

    it('enforces the bounded multipart request and per-file size limits', async () => {
      const oversizedLength = await postUpload(
        uploadRequest({ contentLength: '10065537' }),
      )
      const oversizedStream = await postUpload(bodyLimitRequest())
      const oversizedFile = await postUpload(
        uploadRequest({ contents: new Uint8Array(2_000_001) }),
      )

      await expectPrivateFailure(
        oversizedLength,
        HTTP_STATUS_CODE.payloadTooLarge,
        'attachment_too_large',
      )
      await expectPrivateFailure(
        oversizedStream,
        HTTP_STATUS_CODE.payloadTooLarge,
        'attachment_too_large',
      )
      await expectPrivateFailure(
        oversizedFile,
        HTTP_STATUS_CODE.payloadTooLarge,
        'attachment_too_large',
      )
      expect(ports.getMentorScopedService).not.toHaveBeenCalled()
    })

    it('rejects invalid fields, empty files, unsupported extensions and upload keys', async () => {
      const malformedFields = await postUpload(uploadRequest({ extraField: true }))
      const malformedKey = await postUpload(uploadRequest({ uploadKey: 'not-a-uuid' }))
      const emptyFile = await postUpload(
        uploadRequest({ contents: '', filename: 'vazio.txt' }),
      )
      const unsupportedExtension = await postUpload(
        uploadRequest({ filename: 'script.html', mediaType: 'text/html' }),
      )

      await expectPrivateFailure(
        malformedFields,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_attachment',
      )
      await expectPrivateFailure(
        malformedKey,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_attachment',
      )
      await expectPrivateFailure(
        emptyFile,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_attachment',
      )
      await expectPrivateFailure(
        unsupportedExtension,
        HTTP_STATUS_CODE.unprocessableEntity,
        'unsupported_attachment',
      )
      expect(ports.getMentorScopedService).not.toHaveBeenCalled()
    })

    it('forwards authenticated uploads with a normalized media type and safe headers', async () => {
      const attachment = {
        attachment_id: ATTACHMENT_ID,
        filename: 'anotacao.txt',
        media_type: 'text/plain',
        size_bytes: 9,
        status: 'processing',
      }
      ports.uploadMentorAttachment.mockResolvedValue({ attachment, statusCode: 201 })
      const request = uploadRequest({ mediaType: 'application/octet-stream' })
      const response = await postUpload(request)

      expect(ports.getMentorScopedService).toHaveBeenCalledWith(
        request,
        undefined,
        TELEMETRY_CONTEXT,
      )
      expect(ports.uploadMentorAttachment).toHaveBeenCalledOnce()
      const [token, batchId, uploadKey, file, signal] =
        ports.uploadMentorAttachment.mock.calls[0] ?? []
      expect(token).toBe('private-access-token')
      expect(batchId).toBe(BATCH_ID)
      expect(uploadKey).toBe(UPLOAD_KEY)
      expect(file).toBeInstanceOf(File)
      expect(file).toMatchObject({ name: 'anotacao.txt', type: 'text/plain' })
      expect(signal).toBe(request.signal)
      expect(response.status).toBe(201)
      expect(response.headers.get('cache-control')).toBe('private, no-store')
      expect(response.headers.get('x-content-type-options')).toBe('nosniff')
      expect(response.headers.get('content-type')).toContain('application/json')
      expect(await response.json()).toEqual(attachment)
    })

    it('maps the REST upload through the registered handler', async () => {
      const postFormData = vi.fn().mockResolvedValue(
        new RestResponse({
          body: {
            attachment_id: ATTACHMENT_ID,
            filename: 'anotacao.txt',
            media_type: 'text/plain',
            size_bytes: 9,
            status: 'processing',
            failure_code: null,
            analyzed_pages: [],
            illegible_pages: [],
            uninterpreted_pages: [],
          },
          statusCode: 201,
        }),
      )
      const restClient = { postFormData } as unknown as RestClient
      ports.getMentorScopedService.mockResolvedValueOnce({
        accessToken: 'private-access-token',
        service: IntelligenceService(restClient),
      })
      const request = uploadRequest({ mediaType: 'application/octet-stream' })
      vi.stubGlobal('FormData', CapturedFormData)

      const response = await postUpload(request)

      expect(postFormData).toHaveBeenCalledOnce()
      const [path, body, options] = postFormData.mock.calls[0] ?? []
      expect(path).toBe(`/intelligence/mentor-attachment-batches/${BATCH_ID}/attachments`)
      expect(body).toBeInstanceOf(CapturedFormData)
      expect((body as CapturedFormData).get('upload_key')).toBe(UPLOAD_KEY)
      expect((body as CapturedFormData).get('file')).toMatchObject({
        name: 'anotacao.txt',
        type: 'text/plain',
      })
      expect(options).toMatchObject({
        headers: {
          Authorization: 'Bearer private-access-token',
          'Cache-Control': 'no-store',
        },
        signal: request.signal,
      })
      expect(response.status).toBe(201)
      expect(await response.json()).toEqual({
        attachmentId: ATTACHMENT_ID,
        filename: 'anotacao.txt',
        mediaType: 'text/plain',
        sizeBytes: 9,
        status: 'processing',
        failureCode: null,
        analyzedPages: [],
        illegiblePages: [],
        uninterpretedPages: [],
      })
    })

    it('maps an upstream upload failure through the registered handler', async () => {
      const postFormData = vi.fn().mockResolvedValue(
        new RestResponse({
          statusCode: HTTP_STATUS_CODE.conflict,
          errorMessage: 'The attachment is not ready.',
        }),
      )
      const restClient = { postFormData } as unknown as RestClient
      ports.getMentorScopedService.mockResolvedValueOnce({
        accessToken: 'private-access-token',
        service: IntelligenceService(restClient),
      })
      vi.stubGlobal('FormData', CapturedFormData)

      const response = await postUpload()

      expect(postFormData).toHaveBeenCalledOnce()
      await expectPrivateFailure(
        response,
        HTTP_STATUS_CODE.conflict,
        'attachment_not_ready',
      )
    })

    it('maps authentication, upstream status and unexpected failures safely', async () => {
      ports.getMentorScopedService.mockRejectedValueOnce(
        new AppError('Sessão encerrada', 'Erro de autenticação'),
      )
      const unauthenticated = await postUpload()
      ports.uploadMentorAttachment.mockRejectedValueOnce(new RestError('Not ready', 409))
      const conflict = await postUpload()
      ports.uploadMentorAttachment.mockRejectedValueOnce(
        new RestError('Private detail', 500),
      )
      const unexpected = await postUpload()

      await expectPrivateFailure(
        unauthenticated,
        HTTP_STATUS_CODE.unauthorized,
        'unauthenticated',
      )
      await expectPrivateFailure(
        conflict,
        HTTP_STATUS_CODE.conflict,
        'attachment_not_ready',
      )
      const unexpectedBody = await expectPrivateFailure(
        unexpected,
        HTTP_STATUS_CODE.serviceUnavailable,
        'attachment_unavailable',
      )
      expect(unexpectedBody).not.toHaveProperty('message', 'Private detail')
    })
  })

  describe('file read', () => {
    it('rejects malformed identifiers and preview values before service access', async () => {
      const malformedId = await getFile(fileRequest(), 'invalid-session')
      const malformedPreview = await getFile(fileRequest('maybe'))

      await expectPrivateFailure(
        malformedId,
        HTTP_STATUS_CODE.notFound,
        'attachment_not_found',
      )
      await expectPrivateFailure(
        malformedPreview,
        HTTP_STATUS_CODE.unprocessableEntity,
        'malformed_attachment',
      )
      expect(ports.getMentorScopedService).not.toHaveBeenCalled()
      expect(ports.readMentorAttachmentFile).not.toHaveBeenCalled()
    })

    it('serves validated image previews and downloads with private safe headers', async () => {
      ports.readMentorAttachmentFile
        .mockResolvedValueOnce({
          body: new Blob(['imagem']),
          statusCode: 200,
          headers: {
            'content-type': 'IMAGE/PNG; charset=binary',
            'content-disposition':
              "attachment; filename*=UTF-8''folder%2Frelat%C3%B3rio%0A.png",
          },
        })
        .mockResolvedValueOnce({
          body: new Blob(['texto']),
          statusCode: 200,
          headers: { 'content-type': 'text/plain', 'content-disposition': 'attachment' },
        })
      const previewRequest = fileRequest('true')
      const preview = await getFile(previewRequest)
      const downloadRequest = fileRequest()
      const download = await getFile(downloadRequest)

      expect(ports.getMentorScopedService).toHaveBeenCalledWith(
        previewRequest,
        undefined,
        TELEMETRY_CONTEXT,
      )
      expect(ports.readMentorAttachmentFile).toHaveBeenNthCalledWith(
        1,
        'private-access-token',
        SESSION_ID,
        ATTACHMENT_ID,
        true,
        previewRequest.signal,
      )
      expect(preview.status).toBe(200)
      expect(preview.headers.get('content-type')).toBe('image/png')
      expect(preview.headers.get('content-disposition')).toBe(
        "inline; filename*=UTF-8''relat%C3%B3rio.png",
      )
      expect(preview.headers.get('cache-control')).toBe('private, no-store')
      expect(preview.headers.get('x-content-type-options')).toBe('nosniff')
      expect(await preview.text()).toBe('imagem')
      expect(download.headers.get('content-disposition')).toBe(
        "attachment; filename*=UTF-8''anexo",
      )
      expect(await download.text()).toBe('texto')
    })

    it('maps a REST file response through the registered handler', async () => {
      const getFileResponse = vi.fn().mockResolvedValue(
        new RestResponse({
          body: new Blob(['imagem']),
          statusCode: 200,
          headers: {
            'content-type': 'image/png',
            'content-disposition': "attachment; filename*=UTF-8''imagem.png",
          },
        }),
      )
      const restClient = { getFile: getFileResponse } as unknown as RestClient
      ports.getMentorScopedService.mockResolvedValueOnce({
        accessToken: 'private-access-token',
        service: IntelligenceService(restClient),
      })
      const request = fileRequest('true')

      const response = await getFile(request)

      expect(getFileResponse).toHaveBeenCalledWith(
        `/intelligence/mentor-sessions/${SESSION_ID}/attachments/${ATTACHMENT_ID}/file`,
        {
          headers: {
            Authorization: 'Bearer private-access-token',
            'Cache-Control': 'no-store',
          },
          params: { preview: true },
          signal: request.signal,
        },
      )
      expect(response.status).toBe(200)
      expect(response.headers.get('content-type')).toBe('image/png')
      expect(response.headers.get('content-disposition')).toBe(
        "inline; filename*=UTF-8''imagem.png",
      )
      expect(await response.text()).toBe('imagem')
    })

    it('maps an upstream file failure through the registered handler', async () => {
      const getFileResponse = vi.fn().mockResolvedValue(
        new RestResponse({
          statusCode: HTTP_STATUS_CODE.conflict,
          errorMessage: 'The attachment is not ready.',
        }),
      )
      const restClient = { getFile: getFileResponse } as unknown as RestClient
      ports.getMentorScopedService.mockResolvedValueOnce({
        accessToken: 'private-access-token',
        service: IntelligenceService(restClient),
      })

      const response = await getFile()

      expect(getFileResponse).toHaveBeenCalledOnce()
      await expectPrivateFailure(
        response,
        HTTP_STATUS_CODE.conflict,
        'attachment_not_ready',
      )
    })

    it('rejects unsupported media types and non-image previews', async () => {
      ports.readMentorAttachmentFile
        .mockResolvedValueOnce({
          body: new Blob(['unsafe']),
          statusCode: 200,
          headers: {
            'content-type': 'text/html',
            'content-disposition': 'filename="x.html"',
          },
        })
        .mockResolvedValueOnce({
          body: new Blob(['text']),
          statusCode: 200,
          headers: {
            'content-type': 'text/plain',
            'content-disposition': 'filename="x.txt"',
          },
        })
      const unsupported = await getFile()
      const nonImagePreview = await getFile(fileRequest('true'))

      await expectPrivateFailure(
        unsupported,
        HTTP_STATUS_CODE.serviceUnavailable,
        'attachment_unavailable',
      )
      await expectPrivateFailure(
        nonImagePreview,
        HTTP_STATUS_CODE.unprocessableEntity,
        'unsupported_attachment_preview',
      )
    })

    it('maps not-ready and unexpected read failures to safe responses', async () => {
      ports.readMentorAttachmentFile.mockRejectedValueOnce(
        new RestError('Not ready', 409),
      )
      const notReady = await getFile()
      ports.readMentorAttachmentFile.mockRejectedValueOnce(new Error('Private details'))
      const unexpected = await getFile()

      await expectPrivateFailure(
        notReady,
        HTTP_STATUS_CODE.conflict,
        'attachment_not_ready',
      )
      const unexpectedBody = await expectPrivateFailure(
        unexpected,
        HTTP_STATUS_CODE.serviceUnavailable,
        'attachment_unavailable',
      )
      expect(unexpectedBody).not.toHaveProperty('message', 'Private details')
    })
  })
})
