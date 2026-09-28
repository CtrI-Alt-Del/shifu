import { useCallback, useState } from 'react'

import { ROUTES } from '@/constants/routes'
import { AuthError } from '@/core/errors/auth-error'

export type PasswordResetResult =
  | {
      redirectTo: typeof ROUTES.login
      result: 'reset'
      requiresEmailConfirmation: boolean
    }
  | { result: 'expired' | 'used' | 'invalid' }

export type PasswordResetLinkStatus = { result: 'valid' | 'expired' | 'used' | 'invalid' }

export const useResetPasswordAction = () => {
  const [error, setError] = useState<AuthError | null>(null)
  const [isPending, setIsPending] = useState(false)

  const handleResetPassword = useCallback(
    async (token: string, password: string, passwordConfirmation: string) => {
      setError(null)
      setIsPending(true)
      try {
        if (!isRecoveryToken(token)) return { result: 'invalid' as const }
        return await requestRecoveryJson<PasswordResetResult>(
          '/api/auth/password-reset',
          {
            body: { password, passwordConfirmation, token },
            method: 'POST',
          },
          parsePasswordResetResult,
          'Não foi possível redefinir sua senha agora. Tente novamente.',
        )
      } catch (cause) {
        const authError =
          cause instanceof AuthError
            ? cause
            : new AuthError(
                'unavailable',
                'Não foi possível redefinir sua senha agora. Tente novamente.',
                { cause },
              )
        setError(authError)
        throw authError
      } finally {
        setIsPending(false)
      }
    },
    [],
  )

  const handleGetPasswordResetLinkStatus = useCallback(async (token: string) => {
    setError(null)
    setIsPending(true)
    try {
      if (!isRecoveryToken(token)) return { result: 'invalid' as const }
      return await requestRecoveryJson<PasswordResetLinkStatus>(
        '/api/auth/password-reset-link/status',
        { body: { token }, method: 'POST' },
        parsePasswordResetLinkStatus,
        'Não foi possível verificar este link agora. Tente novamente.',
      )
    } catch (cause) {
      const authError =
        cause instanceof AuthError
          ? cause
          : new AuthError(
              'unavailable',
              'Não foi possível verificar este link agora. Tente novamente.',
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
    getPasswordResetLinkStatus: handleGetPasswordResetLinkStatus,
    isPending,
    resetPassword: handleResetPassword,
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

function parsePasswordResetResult(result: unknown): PasswordResetResult | null {
  if (!isRecord(result)) return null
  if (result.result === 'reset') {
    return typeof result.requiresEmailConfirmation === 'boolean' &&
      result.redirectTo === ROUTES.login
      ? {
          redirectTo: result.redirectTo,
          requiresEmailConfirmation: result.requiresEmailConfirmation,
          result: 'reset',
        }
      : null
  }
  return result.result === 'expired' ||
    result.result === 'used' ||
    result.result === 'invalid'
    ? { result: result.result }
    : null
}

function parsePasswordResetLinkStatus(result: unknown): PasswordResetLinkStatus | null {
  return isRecord(result) &&
    (result.result === 'valid' ||
      result.result === 'expired' ||
      result.result === 'used' ||
      result.result === 'invalid')
    ? { result: result.result }
    : null
}

function isRecoveryToken(value: string) {
  return /^[A-Za-z0-9_-]{43}$/.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
