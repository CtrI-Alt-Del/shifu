import { AuthError } from '@/core/errors/auth-error'

export const PENDING_COOKIE_NAME = 'shifu-pending-flow'

export type PendingConfirmationStatus = {
  state: 'ready' | 'cooldown' | 'delivery_issue'
  hasPendingContext: boolean
}

export async function getPendingConfirmationStatus(
  request: Request,
  handleAuthRequest: (request: Request) => Promise<Response>,
): Promise<PendingConfirmationStatus> {
  if (!hasPendingConfirmationCookie(request)) {
    return { state: 'delivery_issue', hasPendingContext: false }
  }

  const response = await handleAuthRequest(
    new Request(new URL('/api/auth/pending-confirmation', request.url), {
      headers: request.headers,
    }),
  )
  if (!response.ok) {
    throw new AuthError('unavailable', 'Não foi possível validar a confirmação.', {
      statusCode: response.status,
    })
  }

  const result: unknown = await response.json()
  if (
    !isRecord(result) ||
    (result.state !== 'ready' &&
      result.state !== 'cooldown' &&
      result.state !== 'delivery_issue') ||
    typeof result.hasPendingContext !== 'boolean'
  ) {
    throw new AuthError('invalid-response', 'Resposta de confirmação inválida.')
  }

  return {
    state: result.state,
    hasPendingContext: result.hasPendingContext,
  }
}

function hasPendingConfirmationCookie(request: Request): boolean {
  return (request.headers.get('cookie') ?? '').split(';').some((cookie) => {
    const separator = cookie.indexOf('=')
    return separator >= 0 && cookie.slice(0, separator).trim() === PENDING_COOKIE_NAME
  })
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
