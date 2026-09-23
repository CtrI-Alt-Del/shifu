import type { RestClient } from '@/core/shared/interfaces/rest-client'
import { AuthError } from '@/core/errors/auth-error'

export type IdentityProfile = {
  account_id: string
  display_name: string
  email: string
  time_zone: string | null
  status: string
  created_at: string
  confirmed_at: string | null
}

export type IdentityAuthentication = {
  profile: IdentityProfile
  access: 'protected' | 'activation-only'
  access_version: number
}

export type CurrentIdentitySession = {
  account_id: string
  display_name: string
  time_zone: string | null
}

export type PendingConfirmationStatus = {
  state: 'ready' | 'cooldown' | 'delivery_issue'
  retry_after_seconds: number | null
}

export type ResendConfirmationResult = {
  result: 'accepted' | 'cooldown'
  retry_after_seconds: number | null
}

export type EmailConfirmationResult =
  | {
      result: 'activated'
      profile: Pick<
        IdentityProfile,
        'account_id' | 'display_name' | 'email' | 'time_zone'
      >
      access_version: number
    }
  | { result: 'expired' | 'used' | 'invalid' }

export type IdentityService = ReturnType<typeof IdentityService>

export const IdentityService = (restClient: RestClient) => {
  function validateAuthenticationResponse(body: unknown): IdentityAuthentication {
    if (!isRecord(body) || !isRecord(body.profile)) {
      throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.')
    }

    const profile = body.profile
    if (
      typeof profile.account_id !== 'string' ||
      typeof profile.display_name !== 'string' ||
      typeof profile.email !== 'string' ||
      (profile.time_zone !== null && typeof profile.time_zone !== 'string') ||
      typeof profile.status !== 'string' ||
      typeof profile.created_at !== 'string' ||
      (profile.confirmed_at !== null && typeof profile.confirmed_at !== 'string') ||
      (body.access !== 'protected' && body.access !== 'activation-only') ||
      typeof body.access_version !== 'number' ||
      !Number.isInteger(body.access_version) ||
      body.access_version < 1
    ) {
      throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.')
    }

    return {
      profile: profile as IdentityProfile,
      access: body.access,
      access_version: body.access_version,
    }
  }

  function validateCurrentSessionResponse(body: unknown): CurrentIdentitySession {
    if (
      !isRecord(body) ||
      typeof body.account_id !== 'string' ||
      typeof body.display_name !== 'string' ||
      (body.time_zone !== null && typeof body.time_zone !== 'string')
    ) {
      throw new AuthError('invalid-response', 'A resposta de sessão é inválida.')
    }

    return body as unknown as CurrentIdentitySession
  }

  function mapFailure(response: { statusCode: number }): never {
    if (response.statusCode === 401) {
      throw new AuthError('authentication-rejected', 'E-mail ou senha inválidos.', {
        statusCode: response.statusCode,
      })
    }

    if (response.statusCode === 0 || response.statusCode >= 500) {
      throw new AuthError(
        'unavailable',
        'Não foi possível acessar o serviço de identidade.',
        { statusCode: response.statusCode },
      )
    }

    throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.', {
      statusCode: response.statusCode,
    })
  }

  return {
    async validateCredentials(email: string, password: string) {
      const response = await restClient.post<IdentityAuthentication>(
        '/identity/sign-in',
        { email, password },
      )

      if (response.isFailure) mapFailure(response)
      if (!response.body) {
        throw new AuthError('invalid-response', 'A resposta de autenticação é inválida.')
      }

      return validateAuthenticationResponse(response.body)
    },

    async getCurrentSession(accessToken: string) {
      const response = await restClient.get<CurrentIdentitySession>('/identity/session', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })

      if (response.isFailure) mapFailure(response)
      return validateCurrentSessionResponse(response.body)
    },

    async publishMainPageEntered(accessToken: string) {
      const response = await restClient.post<void>(
        '/identity/main-page-entries',
        undefined,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) mapFailure(response)
    },

    async registerAccount(input: {
      displayName: string
      email: string
      password: string
    }) {
      const response = await restClient.post<{
        result: 'pending'
        pending_handle: string
      }>('/identity/registrations', {
        display_name: input.displayName,
        email: input.email,
        password: input.password,
      })

      if (response.isFailure || !response.body) mapFailure(response)
      if (
        response.body.result !== 'pending' ||
        typeof response.body.pending_handle !== 'string' ||
        !/^[A-Za-z0-9_-]{43}$/.test(response.body.pending_handle)
      ) {
        throw new AuthError('invalid-response', 'A resposta de cadastro é inválida.')
      }

      return response.body
    },

    async getPendingConfirmationStatus(pendingHandle: string) {
      const response = await restClient.post<PendingConfirmationStatus>(
        '/identity/pending-confirmations/status',
        { pending_handle: pendingHandle },
      )

      if (response.isFailure || !response.body) mapFailure(response)
      return validatePendingStatusResponse(response.body)
    },

    async resendConfirmation(pendingHandle: string) {
      const response = await restClient.post<ResendConfirmationResult>(
        '/identity/pending-confirmations/resend',
        { pending_handle: pendingHandle },
      )

      if (response.isFailure || !response.body) mapFailure(response)
      return validateResendResponse(response.body)
    },

    async confirmEmail(token: string) {
      const response = await restClient.post<EmailConfirmationResult>(
        '/identity/email-confirmations',
        { token },
      )

      if (response.isFailure || !response.body) mapFailure(response)
      return validateConfirmationResponse(response.body)
    },
  }
}

function validatePendingStatusResponse(body: unknown): PendingConfirmationStatus {
  if (
    !isRecord(body) ||
    (body.state !== 'ready' &&
      body.state !== 'cooldown' &&
      body.state !== 'delivery_issue') ||
    (body.retry_after_seconds !== null && typeof body.retry_after_seconds !== 'number')
  ) {
    throw new AuthError('invalid-response', 'A resposta de confirmação é inválida.')
  }

  return body as unknown as PendingConfirmationStatus
}

function validateResendResponse(body: unknown): ResendConfirmationResult {
  if (
    !isRecord(body) ||
    (body.result !== 'accepted' && body.result !== 'cooldown') ||
    (body.retry_after_seconds !== null && typeof body.retry_after_seconds !== 'number')
  ) {
    throw new AuthError('invalid-response', 'A resposta de confirmação é inválida.')
  }

  return body as unknown as ResendConfirmationResult
}

function validateConfirmationResponse(body: unknown): EmailConfirmationResult {
  if (!isRecord(body) || typeof body.result !== 'string') {
    throw new AuthError('invalid-response', 'A resposta de confirmação é inválida.')
  }

  if (body.result === 'expired' || body.result === 'used' || body.result === 'invalid') {
    return { result: body.result }
  }

  if (
    body.result !== 'activated' ||
    !isRecord(body.profile) ||
    typeof body.profile.account_id !== 'string' ||
    typeof body.profile.display_name !== 'string' ||
    typeof body.profile.email !== 'string' ||
    (body.profile.time_zone !== null && typeof body.profile.time_zone !== 'string') ||
    typeof body.access_version !== 'number' ||
    !Number.isInteger(body.access_version) ||
    body.access_version < 1
  ) {
    throw new AuthError('invalid-response', 'A resposta de confirmação é inválida.')
  }

  return body as unknown as EmailConfirmationResult
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
