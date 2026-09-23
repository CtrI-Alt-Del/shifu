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

export type RegisterAccountInput = {
  displayName: string
  email: string
  password: string
}

export type PendingConfirmationStatus = {
  state: 'ready' | 'cooldown' | 'delivery_issue'
  retryAfterSeconds: number | null
}

export type ResendConfirmationResult = {
  result: 'accepted' | 'cooldown'
  retryAfterSeconds: number | null
}

export type ConfirmEmailResult = {
  result: 'activated' | 'expired' | 'used' | 'invalid'
  redirectTo: RouteName
}

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

  async function registerAccount(input: RegisterAccountInput) {
    return requestJson<{ redirectTo: typeof ROUTES.pendingConfirmation }>(
      '/api/auth/register/identity',
      { method: 'POST', body: input },
      (result) =>
        isRecord(result) && result.redirectTo === ROUTES.pendingConfirmation
          ? { redirectTo: result.redirectTo }
          : null,
      'Não foi possível criar sua conta agora. Tente novamente.',
    )
  }

  async function getPendingConfirmationStatus(): Promise<PendingConfirmationStatus> {
    return requestJson(
      '/api/auth/pending-confirmation',
      { method: 'GET' },
      (result) => {
        if (
          !isRecord(result) ||
          (result.state !== 'ready' &&
            result.state !== 'cooldown' &&
            result.state !== 'delivery_issue') ||
          (result.retryAfterSeconds !== null &&
            typeof result.retryAfterSeconds !== 'number')
        ) {
          return null
        }
        return result as PendingConfirmationStatus
      },
      'Não foi possível atualizar a confirmação. Tente novamente.',
    )
  }

  async function resendConfirmation(): Promise<ResendConfirmationResult> {
    return requestJson(
      '/api/auth/pending-confirmation/resend',
      { method: 'POST' },
      (result) => {
        if (
          !isRecord(result) ||
          (result.result !== 'accepted' && result.result !== 'cooldown') ||
          (result.retryAfterSeconds !== null &&
            typeof result.retryAfterSeconds !== 'number')
        ) {
          return null
        }
        return result as ResendConfirmationResult
      },
      'Não foi possível reenviar agora. Tente novamente.',
    )
  }

  async function confirmEmail(token: string): Promise<ConfirmEmailResult> {
    return requestJson(
      '/api/auth/confirm-email',
      { method: 'POST', body: { token } },
      (result) => {
        if (
          !isRecord(result) ||
          (result.result !== 'activated' &&
            result.result !== 'expired' &&
            result.result !== 'used' &&
            result.result !== 'invalid') ||
          !isRoutePath(result.redirectTo)
        ) {
          return null
        }
        return {
          result: result.result,
          redirectTo: result.redirectTo === ROUTES.root ? 'root' : 'login',
        }
      },
      'Não foi possível confirmar agora. Tente novamente.',
    )
  }

  return {
    confirmEmail,
    getPendingConfirmationStatus,
    registerAccount,
    resendConfirmation,
    signIn,
  }
}

async function requestJson<Result>(
  path: string,
  options: { method: 'GET' | 'POST'; body?: unknown },
  parse: (result: unknown) => Result | null,
  unavailableMessage: string,
): Promise<Result> {
  let response: Response
  try {
    response = await fetch(path, {
      method: options.method,
      credentials: 'same-origin',
      headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
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
  if (!result) {
    throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.', {
      statusCode: response.status,
    })
  }
  return result
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isRoutePath(value: unknown): value is (typeof ROUTES)[RouteName] {
  return Object.values(ROUTES).includes(value as (typeof ROUTES)[RouteName])
}
