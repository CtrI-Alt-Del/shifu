import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'
import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const MAX_ATTACHMENT_BYTES = 10_000_000
const MAX_MULTIPART_OVERHEAD_BYTES = 65_536
const MAX_MULTIPART_BODY_BYTES = MAX_ATTACHMENT_BYTES + MAX_MULTIPART_OVERHEAD_BYTES
const ULID_PATTERN = /^[0-9A-HJKMNP-TV-Z]{26}$/
const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const MEDIA_TYPES_BY_EXTENSION: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.pdf': 'application/pdf',
  '.json': 'application/json',
  '.csv': 'text/csv',
  '.txt': 'text/plain',
}
const ALLOWED_MEDIA_TYPES = new Set(Object.values(MEDIA_TYPES_BY_EXTENSION))
const RESPONSE_HEADERS = {
  'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff',
}

type Failure = { code: string; message: string }

export async function handleMentorAttachmentUpload(
  request: Request,
  batchId: string,
): Promise<Response> {
  if (!ULID_PATTERN.test(batchId))
    return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
      code: 'malformed_attachment',
      message: 'Não foi possível ler este arquivo.',
    })
  if (!isSameOriginRequest(request))
    return jsonFailure(HTTP_STATUS_CODE.forbidden, {
      code: 'same_origin_required',
      message: 'Não foi possível enviar o arquivo.',
    })

  const contentLength = request.headers.get('content-length')
  if (contentLength !== null) {
    if (!/^\d+$/.test(contentLength))
      return jsonFailure(HTTP_STATUS_CODE.badRequest, {
        code: 'malformed_attachment',
        message: 'Não foi possível ler este arquivo.',
      })
    if (Number(contentLength) > MAX_MULTIPART_BODY_BYTES)
      return jsonFailure(HTTP_STATUS_CODE.payloadTooLarge, {
        code: 'attachment_too_large',
        message: 'O arquivo excede o limite de 10 MB.',
      })
  }

  let body: Uint8Array
  try {
    body = await readBoundedBody(request, MAX_MULTIPART_BODY_BYTES)
  } catch {
    if (request.signal.aborted)
      return new Response(null, { status: 499, headers: RESPONSE_HEADERS })
    return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
      code: 'malformed_attachment',
      message: 'Não foi possível ler este arquivo.',
    })
  }
  if (body.byteLength > MAX_MULTIPART_BODY_BYTES)
    return jsonFailure(HTTP_STATUS_CODE.payloadTooLarge, {
      code: 'attachment_too_large',
      message: 'O arquivo excede o limite de 10 MB.',
    })

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
      code: 'malformed_attachment',
      message: 'Não foi possível ler este arquivo.',
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
      code: 'malformed_attachment',
      message: 'Não foi possível ler este arquivo.',
    })
  if (file.size > MAX_ATTACHMENT_BYTES)
    return jsonFailure(HTTP_STATUS_CODE.payloadTooLarge, {
      code: 'attachment_too_large',
      message: 'O arquivo excede o limite de 10 MB.',
    })
  if (file.size === 0)
    return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
      code: 'malformed_attachment',
      message: 'Não foi possível ler este arquivo.',
    })

  const extension = getExtension(file.name)
  const mediaType = MEDIA_TYPES_BY_EXTENSION[extension]
  if (!mediaType || !ALLOWED_MEDIA_TYPES.has(mediaType))
    return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
      code: 'unsupported_attachment',
      message: 'Este formato de arquivo não é aceito.',
    })

  try {
    const { accessToken, service } = await getMentorScopedService(request)
    const normalizedFile =
      file.type.toLowerCase() === mediaType
        ? file
        : new File([file], file.name, { type: mediaType })
    const result = await service.uploadMentorAttachment(
      accessToken,
      batchId,
      uploadKey,
      normalizedFile,
      request.signal,
    )
    return new Response(JSON.stringify(result.attachment), {
      status: result.statusCode,
      headers: { ...RESPONSE_HEADERS, 'Content-Type': 'application/json' },
    })
  } catch (error) {
    return attachmentFailureResponse(error)
  }
}

export async function handleMentorAttachmentFile(
  request: Request,
  sessionId: string,
  attachmentId: string,
): Promise<Response> {
  const headers = { ...RESPONSE_HEADERS }
  if (!ULID_PATTERN.test(sessionId) || !ULID_PATTERN.test(attachmentId))
    return jsonFailure(HTTP_STATUS_CODE.notFound, {
      code: 'attachment_not_found',
      message: 'Este arquivo não está disponível nesta conversa.',
    })

  const url = new URL(request.url)
  const rawPreview = url.searchParams.get('preview')
  if (rawPreview !== null && rawPreview !== 'true' && rawPreview !== 'false')
    return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
      code: 'malformed_attachment',
      message: 'Não foi possível abrir este arquivo.',
    })
  const preview = rawPreview === 'true'

  try {
    const { accessToken, service } = await getMentorScopedService(request)
    const result = await service.readMentorAttachmentFile(
      accessToken,
      sessionId,
      attachmentId,
      preview,
      request.signal,
    )
    const mediaType = safeMediaType(result.headers['content-type'])
    if (!mediaType)
      return jsonFailure(HTTP_STATUS_CODE.serviceUnavailable, {
        code: 'attachment_unavailable',
        message: 'Não foi possível abrir este arquivo. Tente novamente.',
      })
    if (preview && !mediaType.startsWith('image/'))
      return jsonFailure(HTTP_STATUS_CODE.unprocessableEntity, {
        code: 'unsupported_attachment_preview',
        message: 'A prévia está disponível apenas para imagens.',
      })

    const filename = safeFilename(result.headers['content-disposition'])
    const disposition = preview ? 'inline' : 'attachment'
    const fileHeaders = new Headers({
      ...headers,
      'Content-Type': mediaType,
      'Content-Disposition': `${disposition}; filename*=UTF-8''${encodeURIComponent(filename)}`,
    })
    return new Response(result.body, { status: result.statusCode, headers: fileHeaders })
  } catch (error) {
    return attachmentFailureResponse(error)
  }
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

function getExtension(filename: string): string {
  const separator = filename.lastIndexOf('.')
  return separator < 0 ? '' : filename.slice(separator).toLowerCase()
}

function safeMediaType(value: string | undefined): string | null {
  const mediaType = value?.split(';', 1)[0]?.trim().toLowerCase()
  return mediaType && ALLOWED_MEDIA_TYPES.has(mediaType) ? mediaType : null
}

function safeFilename(disposition: string | undefined): string {
  const encoded = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  const plain = disposition?.match(/filename="?([^";]+)"?/i)?.[1]
  let filename = 'anexo'
  try {
    filename = encoded ? decodeURIComponent(encoded) : (plain ?? filename)
  } catch {
    filename = plain ?? filename
  }
  const safe = filename
    .split(/[\\/]/)
    .at(-1)
    ?.split('')
    .filter((character) => {
      const code = character.charCodeAt(0)
      return code >= 0x20 && code !== 0x7f
    })
    .join('')
    .trim()
    .slice(0, 200)
  return safe || 'anexo'
}

function attachmentFailureResponse(error: unknown): Response {
  const statusCode =
    error instanceof RestError
      ? allowedFailureStatus(error.statusCode)
      : error instanceof AppError && error.title === 'Erro de autenticação'
        ? HTTP_STATUS_CODE.unauthorized
        : HTTP_STATUS_CODE.serviceUnavailable
  const failure = failureForStatus(statusCode)
  return jsonFailure(statusCode, failure)
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

function failureForStatus(statusCode: number): Failure {
  const failures: Record<number, Failure> = {
    [HTTP_STATUS_CODE.unauthorized]: {
      code: 'unauthenticated',
      message: 'Sua sessão expirou. Atualize a página.',
    },
    [HTTP_STATUS_CODE.forbidden]: {
      code: 'inactive_account',
      message: 'Sua conta não pode acessar este arquivo.',
    },
    [HTTP_STATUS_CODE.notFound]: {
      code: 'attachment_not_found',
      message: 'Este arquivo não está disponível nesta conversa.',
    },
    [HTTP_STATUS_CODE.conflict]: {
      code: 'attachment_not_ready',
      message: 'O arquivo ainda está sendo preparado.',
    },
    [HTTP_STATUS_CODE.payloadTooLarge]: {
      code: 'attachment_too_large',
      message: 'O arquivo excede o limite de 10 MB.',
    },
    [HTTP_STATUS_CODE.unprocessableEntity]: {
      code: 'unsupported_attachment',
      message: 'Não foi possível processar este arquivo.',
    },
  }
  return (
    failures[statusCode] ?? {
      code: 'attachment_unavailable',
      message: 'Não foi possível concluir agora. Tente novamente.',
    }
  )
}

function jsonFailure(statusCode: number, failure: Failure): Response {
  return new Response(JSON.stringify(failure), {
    status: statusCode,
    headers: { ...RESPONSE_HEADERS, 'Content-Type': 'application/json' },
  })
}
