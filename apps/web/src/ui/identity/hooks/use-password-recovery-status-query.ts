import { useEffect, useRef, useState } from 'react'

import { useQuery } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'

import type { PasswordRecoveryStatus } from './use-request-password-recovery-action'

const PASSWORD_RECOVERY_CONTEXT_LIFETIME_MS = 60 * 60 * 1000

export const usePasswordRecoveryStatusQuery = (enabled: boolean) => {
  const enabledRef = useRef(false)
  const [contextExpiresAt, setContextExpiresAt] = useState<number | null>(null)
  const [isContextExpired, setIsContextExpired] = useState(false)
  const query = useQuery({
    enabled: enabled && !isContextExpired,
    queryFn: async () =>
      requestRecoveryStatus('Não foi possível atualizar a recuperação. Tente novamente.'),
    queryKey: ['identity', 'password-recovery-status'],
    refetchInterval: (_statusQuery) => {
      if (!enabled || isContextExpired || contextExpiresAt === null) {
        return false
      }

      const remainingMilliseconds = contextExpiresAt - Date.now()
      return remainingMilliseconds > 10_000 ? 10_000 : false
    },
    retry: false,
  })

  useEffect(() => {
    if (enabled && !enabledRef.current) {
      setContextExpiresAt(Date.now() + PASSWORD_RECOVERY_CONTEXT_LIFETIME_MS)
      setIsContextExpired(false)
    }
    if (!enabled) {
      setContextExpiresAt(null)
      setIsContextExpired(false)
    }
    enabledRef.current = enabled
  }, [enabled])

  useEffect(() => {
    if (!enabled || contextExpiresAt === null) return

    const remainingMilliseconds = contextExpiresAt - Date.now()
    if (remainingMilliseconds <= 0) {
      setIsContextExpired(true)
      return
    }

    const timeout = window.setTimeout(
      () => setIsContextExpired(true),
      remainingMilliseconds,
    )
    return () => window.clearTimeout(timeout)
  }, [contextExpiresAt, enabled])

  return {
    error: query.error,
    isLoading: query.isPending,
    refetch: query.refetch,
    status: query.data ?? null,
  }
}

async function requestRecoveryStatus(unavailableMessage: string) {
  let response: Response
  try {
    response = await fetch('/api/auth/password-recovery/status', {
      credentials: 'same-origin',
      method: 'GET',
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

  if (
    !isRecord(body) ||
    (body.state !== 'ready' &&
      body.state !== 'cooldown' &&
      body.state !== 'delivery_issue') ||
    (body.retryAfterSeconds !== null && typeof body.retryAfterSeconds !== 'number')
  ) {
    throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.', {
      statusCode: response.status,
    })
  }

  return body as PasswordRecoveryStatus
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
