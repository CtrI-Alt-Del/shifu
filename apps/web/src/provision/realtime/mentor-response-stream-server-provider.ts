import { SERVER_ENV } from '@/constants/server-env'
import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { FetchRestStreamClient } from '@/rest/fetch/fetch-rest-stream-client'
import { IntelligenceService } from '@/rest/services/intelligence-service'

export async function getMentorScopedService(request: Request, accountEmail?: string) {
  const access = await getBetterAuthProvider().getCurrentAccess(request)
  if (!access)
    throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
  if (
    accountEmail &&
    access.email.toLocaleLowerCase() !== accountEmail.toLocaleLowerCase()
  )
    throw new AppError('A sessão da conta mudou. Atualize a página.', 'Escopo alterado')
  return {
    accessToken: access.accessToken,
    service: IntelligenceService(
      AxiosRestClient(SERVER_ENV.shifuServerAppUrl, { withCredentials: false }),
      FetchRestStreamClient(SERVER_ENV.shifuServerAppUrl),
    ),
  }
}
export async function handleMentorResponseStream(
  request: Request,
  sessionId: string,
): Promise<Response> {
  const headers = { 'Cache-Control': 'no-store', 'Content-Type': 'text/event-stream' }
  const cursor =
    request.headers.get('Last-Event-ID') ??
    new URL(request.url).searchParams.get('after_sequence') ??
    '0'
  if (
    !/^\d+$/.test(cursor) ||
    !Number.isSafeInteger(Number(cursor)) ||
    !/^[0-9A-HJKMNP-TV-Z]{26}$/.test(sessionId)
  )
    return new Response(null, { status: 422, headers })
  const transport = new AbortController()
  function abortTransport() {
    transport.abort()
  }
  request.signal.addEventListener('abort', abortTransport, { once: true })
  if (request.signal.aborted) abortTransport()
  try {
    const { accessToken, service } = await getMentorScopedService(request)
    const body = await service.openMentorResponseEvents(
      accessToken,
      { sessionId, afterSequence: Number(cursor) },
      transport.signal,
    )
    const reader = body.getReader()
    const stream = new ReadableStream<Uint8Array>({
      async pull(controller) {
        try {
          const chunk = await reader.read()
          if (chunk.done) {
            request.signal.removeEventListener('abort', abortTransport)
            controller.close()
          } else controller.enqueue(chunk.value)
        } catch {
          request.signal.removeEventListener('abort', abortTransport)
          abortTransport()
          controller.error(
            new AppError(
              'A conexão da resposta foi interrompida.',
              'Erro de comunicação',
            ),
          )
        }
      },
      async cancel() {
        request.signal.removeEventListener('abort', abortTransport)
        abortTransport()
        await reader.cancel()
      },
    })
    return new Response(stream, { headers })
  } catch (error) {
    request.signal.removeEventListener('abort', abortTransport)
    abortTransport()
    const status =
      error instanceof RestError
        ? error.statusCode || 503
        : error instanceof AppError && error.title === 'Erro de autenticação'
          ? 401
          : 503
    return new Response(null, { status, headers })
  }
}
