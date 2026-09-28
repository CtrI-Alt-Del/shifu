import { useCallback, useState } from 'react'

import { AuthError } from '@/core/errors/auth-error'

export type PasswordRecoveryStatus = {
  state: 'ready' | 'cooldown' | 'delivery_issue'
  retryAfterSeconds: number | null
}

type PasswordRecoveryRequestResult = { accepted: true }

export const useRequestPasswordRecoveryAction = () => {
  const [error, setError] = useState<AuthError | null>(null)
  const [isPending, setIsPending] = useState(false)

  const handleRequestPasswordRecovery = useCallback(async (email: string) => {
    setError(null)
    setIsPending(true)
    try {
      return await requestRecoveryJson<PasswordRecoveryRequestResult>(
        '/api/auth/password-recovery',
        { body: { email }, method: 'POST' },
        (result) =>
          isRecord(result) && result.accepted === true ? { accepted: true } : null,
        'Não foi possível solicitar a recuperação agora. Tente novamente.',
      )
    } catch (cause) {
      const authError =
        cause instanceof AuthError
          ? cause
          : new AuthError(
              'unavailable',
              'Não foi possível solicitar a recuperação agora. Tente novamente.',
              { cause },
            )
      setError(authError)
      throw authError
    } finally {
      setIsPending(false)
    }
  }, [])

  const handleRetryPasswordRecovery = useCallback(async () => {
    setError(null)
    setIsPending(true)
    try {
      return await requestRecoveryJson<PasswordRecoveryStatus>(
        '/api/auth/password-recovery/retry',
        { body: {}, method: 'POST' },
        parsePasswordRecoveryStatus,
        'Não foi possível solicitar a recuperação agora. Tente novamente.',
      )
    } catch (cause) {
      const authError =
        cause instanceof AuthError
          ? cause
          : new AuthError(
              'unavailable',
              'Não foi possível solicitar a recuperação agora. Tente novamente.',
              { cause },
            )
      setError(authError)
      throw authError
    } finally {
      setIsPending(false)
    }
  }, [])

  return {
    error,
    isPending,
    requestPasswordRecovery: handleRequestPasswordRecovery,
    retryPasswordRecovery: handleRetryPasswordRecovery,
  }
}

async function requestRecoveryJson<Result>(
  path: string,
  options: { body?: unknown; method: 'GET' | 'POST' },
  parse: (result: unknown) => Result | null,
  unavailableMessage: string,
): Promise<Result> {
  let response: Response
  try {
    response = await fetch(path, {
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: 'same-origin',
      headers:
        options.body === undefined ? undefined : { 'Content-Type': 'application/json' },
      method: options.method,
    })
  } catch (cause) {
    throw new AuthError('unavailable', unavailableMessage, { cause, statusCode: 0 })
  }

  if (!response.ok) {
    throw new AuthError(
      response.status >= 500 ? 'unavailable' : 'invalid-response',
      response.status >= 500
        ? unavailableMessage
        : 'A resposta de autenticação é inválida.',
      { statusCode: response.status },
    )
  }

  let body: unknown
  try {
    body = await response.json()
  } catch (cause) {
    throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.', {
      cause,
      statusCode: response.status,
    })
  }

  const result = parse(body)
  if (result === null) {
    throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.', {
      statusCode: response.status,
    })
  }
  return result
}

function parsePasswordRecoveryStatus(result: unknown): PasswordRecoveryStatus | null {
  if (
    !isRecord(result) ||
    (result.state !== 'ready' &&
      result.state !== 'cooldown' &&
      result.state !== 'delivery_issue') ||
    (result.retryAfterSeconds !== null && typeof result.retryAfterSeconds !== 'number')
  ) {
    return null
  }
  return result as PasswordRecoveryStatus
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
