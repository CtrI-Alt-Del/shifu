import { AuthError } from '@/core/errors/auth-error'

import { ROUTES, type RouteName } from '@/constants/routes'

export type SignInInput = {
  email: string
  password: string
}

export type SignInResult = {
  access: 'protected' | 'activation-only'
  redirectTo: RouteName
}

export type SignInFailure = AuthError

export const CookieSessionAuthProvider = () => {
  async function signIn(input: SignInInput): Promise<SignInResult> {
    let response: Response

    try {
      response = await fetch('/api/auth/sign-in/identity', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      })
    } catch (cause) {
      throw new AuthError(
        'unavailable',
        'Não foi possível entrar agora. Tente novamente.',
        { cause, statusCode: 0 },
      )
    }

    if (response.status === 401) {
      throw new AuthError('authentication-rejected', 'E-mail ou senha inválidos.', {
        statusCode: response.status,
      })
    }

    if (response.status === 429) {
      const retryAfterHeader =
        response.headers.get('Retry-After') ?? response.headers.get('X-Retry-After')
      const retryAfterSeconds = retryAfterHeader ? Number(retryAfterHeader) : undefined

      throw new AuthError(
        'unavailable',
        'Muitas tentativas. Aguarde um momento e tente novamente.',
        {
          retryAfterSeconds:
            retryAfterSeconds !== undefined && Number.isFinite(retryAfterSeconds)
              ? retryAfterSeconds
              : undefined,
          statusCode: response.status,
        },
      )
    }

    if (!response.ok) {
      throw new AuthError(
        response.status >= 500 ? 'unavailable' : 'invalid-response',
        response.status >= 500
          ? 'Não foi possível entrar agora. Tente novamente.'
          : 'A resposta de autenticação é inválida.',
        { statusCode: response.status },
      )
    }

    let result: unknown
    try {
      result = await response.json()
    } catch (cause) {
      throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.', {
        cause,
        statusCode: response.status,
      })
    }

    if (
      !isRecord(result) ||
      (result.access !== 'protected' && result.access !== 'activation-only') ||
      !isRoutePath(result.redirectTo)
    ) {
      throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.', {
        statusCode: response.status,
      })
    }

    return {
      access: result.access,
      redirectTo: result.redirectTo === ROUTES.root ? 'root' : 'pendingConfirmation',
    }
  }

  return { signIn }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isRoutePath(value: unknown): value is (typeof ROUTES)[RouteName] {
  return Object.values(ROUTES).includes(value as (typeof ROUTES)[RouteName])
}
