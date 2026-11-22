import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { AuthError } from '@/core/errors/auth-error'

import { ROUTES, type RouteName } from '@/constants/routes'

export type AccountProfile = {
  accountId: string
  displayName: string
  email: string
  timeZone: string | null
}
export type UpdateAccountProfileInput = { displayName: string; timeZone: string }
export type ChangeAccountPasswordInput = { currentPassword: string; newPassword: string }

export type SignInInput = {
  email: string
  password: string
}

export type SignInResult = {
  access: 'protected' | 'activation-only'
  redirectTo: RouteName
}

export type SignInFailure = AuthError

const LOGOUT_UNAVAILABLE_MESSAGE = 'Não foi possível sair agora. Tente novamente.'
const INVALID_AUTH_RESPONSE_MESSAGE = 'A resposta de autenticação é inválida.'

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

export type AccountErasureStatus = {
  state: 'closed'
  closedAt: string
  erasure: 'pending' | 'completed'
}

export type BrowserDataCapabilityStatus = { state: 'active' | 'revoked' }

export const CookieSessionAuthProvider = () => {
  async function getAccountProfile(): Promise<AccountProfile> {
    return requestAccount('/api/auth/account')
  }
  async function updateAccountProfile(
    input: UpdateAccountProfileInput,
  ): Promise<AccountProfile> {
    return requestAccount('/api/auth/account/profile', input)
  }
  async function changeAccountPassword(
    input: ChangeAccountPasswordInput,
  ): Promise<{ changed: true }> {
    return requestAccount('/api/auth/account/password', input, true)
  }

  async function prepareAccountDeletion(): Promise<void> {
    await requestJson(
      '/api/auth/account/deletion/prepare',
      { method: 'POST', body: {} },
      (result) =>
        isRecord(result) &&
        result.state === 'prepared' &&
        Object.keys(result).length === 1
          ? true
          : null,
      'Não foi possível preparar o encerramento agora. Tente novamente.',
      { cache: 'no-store' },
    )
  }

  async function deleteAccount(currentPassword: string): Promise<AccountErasureStatus> {
    return requestAccountDeletion(
      '/api/auth/account/deletion',
      'POST',
      { currentPassword, confirmed: true },
      'Não foi possível confirmar o encerramento agora. Tente novamente.',
    )
  }

  async function getAccountDeletionStatus(): Promise<AccountErasureStatus> {
    return requestAccountDeletion(
      '/api/auth/account/deletion',
      'GET',
      undefined,
      'Não foi possível consultar o estado do encerramento agora. Tente novamente.',
    )
  }

  async function issueBrowserDataCapability(): Promise<string> {
    return requestJson(
      '/api/identity/browser-data-capabilities',
      { method: 'POST', body: {} },
      (result) =>
        isRecord(result) &&
        typeof result.capability === 'string' &&
        /^[A-Za-z0-9_-]{32,256}$/.test(result.capability) &&
        Object.keys(result).length === 1
          ? result.capability
          : null,
      'Não foi possível validar os dados deste navegador agora. Tente novamente.',
      { cache: 'no-store' },
    )
  }

  async function validateBrowserDataCapability(
    capability: string,
  ): Promise<BrowserDataCapabilityStatus['state']> {
    return requestJson(
      '/api/identity/browser-data-validations',
      { method: 'POST', body: { capability } },
      (result) =>
        isRecord(result) &&
        (result.state === 'active' || result.state === 'revoked') &&
        Object.keys(result).length === 1
          ? result.state
          : null,
      'Não foi possível validar os dados deste navegador agora. Tente novamente.',
      { cache: 'no-store' },
    )
  }

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

  async function signOut(): Promise<void> {
    const response = await postAuthAction('/api/auth/sign-out')
    const result = await readAuthActionResponse(response)

    if (!isRecord(result) || result.success !== true) {
      throw new AuthError('invalid-response', INVALID_AUTH_RESPONSE_MESSAGE, {
        statusCode: response.status,
      })
    }
  }

  async function exitPendingConfirmation(): Promise<void> {
    const response = await postAuthAction('/api/auth/pending-confirmation/sign-out')
    const result = await readAuthActionResponse(response)

    if (!isRecord(result) || Object.keys(result).length !== 0) {
      throw new AuthError('invalid-response', INVALID_AUTH_RESPONSE_MESSAGE, {
        statusCode: response.status,
      })
    }
  }

  async function postAuthAction(path: string): Promise<Response> {
    try {
      const response = await fetch(path, {
        body: '{}',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        method: 'POST',
      })

      if (!response.ok) {
        const isUnavailable = response.status === 429 || response.status >= 500
        throw new AuthError(
          isUnavailable ? 'unavailable' : 'invalid-response',
          isUnavailable ? LOGOUT_UNAVAILABLE_MESSAGE : INVALID_AUTH_RESPONSE_MESSAGE,
          { statusCode: response.status },
        )
      }

      return response
    } catch (cause) {
      if (cause instanceof AuthError) throw cause

      throw new AuthError('unavailable', LOGOUT_UNAVAILABLE_MESSAGE, {
        cause,
        statusCode: 0,
      })
    }
  }

  async function readAuthActionResponse(response: Response): Promise<unknown> {
    try {
      return await response.json()
    } catch (cause) {
      throw new AuthError('invalid-response', INVALID_AUTH_RESPONSE_MESSAGE, {
        cause,
        statusCode: response.status,
      })
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
      { method: 'POST', body: {} },
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
    getAccountProfile,
    updateAccountProfile,
    changeAccountPassword,
    prepareAccountDeletion,
    deleteAccount,
    getAccountDeletionStatus,
    issueBrowserDataCapability,
    validateBrowserDataCapability,
    confirmEmail,
    exitPendingConfirmation,
    getPendingConfirmationStatus,
    registerAccount,
    resendConfirmation,
    signIn,
    signOut,
  }
}

async function requestJson<Result>(
  path: string,
  options: { method: 'GET' | 'POST'; body?: unknown },
  parse: (result: unknown) => Result | null,
  unavailableMessage: string,
  requestOptions: { cache?: RequestCache } = {},
): Promise<Result> {
  let response: Response
  try {
    response = await fetch(path, {
      method: options.method,
      credentials: 'same-origin',
      cache: requestOptions.cache,
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

async function requestAccountDeletion(
  path: string,
  method: 'GET' | 'POST',
  body: unknown,
  unavailableMessage: string,
): Promise<AccountErasureStatus> {
  let response: Response
  try {
    response = await fetch(path, {
      method,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (cause) {
    throw new AuthError(
      method === 'POST' ? 'result-uncertain' : 'unavailable',
      method === 'POST'
        ? 'Não foi possível confirmar o resultado. Verifique o estado antes de tentar novamente.'
        : unavailableMessage,
      { cause, statusCode: 0 },
    )
  }

  let result: unknown
  try {
    result = await response.json()
  } catch (cause) {
    throw new AuthError(
      response.status >= 500 && method === 'POST'
        ? 'result-uncertain'
        : 'invalid-response',
      method === 'POST'
        ? 'Não foi possível confirmar o resultado. Verifique o estado antes de tentar novamente.'
        : 'A resposta de autenticação é inválida.',
      { cause, statusCode: response.status },
    )
  }

  if (!response.ok) {
    if (response.status === 401) {
      throw new AuthError('authentication-rejected', 'Entre novamente para continuar.', {
        statusCode: response.status,
      })
    }
    if (
      response.status === 403 &&
      isRecord(result) &&
      result.code === 'invalid_current_password'
    ) {
      throw new AuthError('invalid-current-password', 'A senha atual está incorreta.', {
        statusCode: response.status,
      })
    }
    if (
      response.status === 403 &&
      isRecord(result) &&
      result.code === 'preparation_expired'
    ) {
      throw new AuthError(
        'validation-failed',
        'A confirmação expirou. Feche e inicie novamente.',
        { statusCode: response.status },
      )
    }
    throw new AuthError(
      method === 'POST' && response.status >= 500 ? 'result-uncertain' : 'unavailable',
      method === 'POST' && response.status >= 500
        ? 'Não foi possível confirmar o resultado. Verifique o estado antes de tentar novamente.'
        : unavailableMessage,
      { statusCode: response.status },
    )
  }

  if (
    !isRecord(result) ||
    result.state !== 'closed' ||
    typeof result.closedAt !== 'string' ||
    Number.isNaN(Date.parse(result.closedAt)) ||
    (result.erasure !== 'pending' && result.erasure !== 'completed') ||
    Object.keys(result).length !== 3
  ) {
    throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.', {
      statusCode: response.status,
    })
  }
  return {
    state: 'closed',
    closedAt: result.closedAt,
    erasure: result.erasure,
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isRoutePath(value: unknown): value is (typeof ROUTES)[RouteName] {
  return Object.values(ROUTES).includes(value as (typeof ROUTES)[RouteName])
}

async function requestAccount(
  path: string,
  input?: UpdateAccountProfileInput,
): Promise<AccountProfile>
async function requestAccount(
  path: string,
  input: ChangeAccountPasswordInput,
  passwordChange: true,
): Promise<{ changed: true }>
async function requestAccount(
  path: string,
  input?: UpdateAccountProfileInput | ChangeAccountPasswordInput,
  passwordChange = false,
): Promise<AccountProfile | { changed: true }> {
  let response: Response
  try {
    response = await fetch(path, {
      method: input ? 'POST' : 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: input ? { 'Content-Type': 'application/json' } : undefined,
      body: input ? JSON.stringify(input) : undefined,
    })
  } catch {
    throw accountTransportError(passwordChange)
  }
  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw accountTransportError(passwordChange, response.status)
  }
  if (!response.ok) {
    if (response.status === HTTP_STATUS_CODE.unauthorized)
      throw new AuthError('authentication-rejected', 'Entre novamente para continuar.', {
        statusCode: 401,
      })
    if (
      isRecord(body) &&
      body.code === 'invalid_current_password' &&
      response.status === HTTP_STATUS_CODE.forbidden
    ) {
      throw new AuthError('invalid-current-password', 'A senha atual está incorreta.', {
        statusCode: 403,
      })
    }
    const fields = {
      invalid_display_name: 'displayName',
      invalid_time_zone: 'timeZone',
      invalid_new_password: 'newPassword',
    } as const
    if (
      isRecord(body) &&
      typeof body.code === 'string' &&
      Object.hasOwn(fields, body.code)
    ) {
      const field = fields[body.code as keyof typeof fields]
      throw new AuthError('validation-failed', 'Confira o campo informado.', {
        field,
        statusCode: response.status,
      })
    }
    if (isRecord(body) && body.code === 'result_uncertain')
      throw accountTransportError(passwordChange, response.status)
    throw new AuthError(
      response.status >= 500 ? 'unavailable' : 'invalid-response',
      'Não foi possível concluir agora. Tente novamente.',
      { statusCode: response.status },
    )
  }
  if (
    passwordChange &&
    isRecord(body) &&
    body.changed === true &&
    Object.keys(body).length === 1
  )
    return { changed: true }
  if (
    !passwordChange &&
    isRecord(body) &&
    typeof body.accountId === 'string' &&
    typeof body.displayName === 'string' &&
    typeof body.email === 'string' &&
    (body.timeZone === null || typeof body.timeZone === 'string') &&
    Object.keys(body).length === 4
  ) {
    return {
      accountId: body.accountId,
      displayName: body.displayName,
      email: body.email,
      timeZone: body.timeZone,
    }
  }
  throw accountTransportError(passwordChange, response.status)
}
function accountTransportError(passwordChange: boolean, statusCode = 0) {
  return new AuthError(
    passwordChange
      ? 'result-uncertain'
      : statusCode === 0 || statusCode >= 500
        ? 'unavailable'
        : 'invalid-response',
    passwordChange
      ? 'Não foi possível confirmar a troca. Verifique seu acesso antes de tentar novamente.'
      : 'Não foi possível carregar os dados da conta.',
    { statusCode },
  )
}
