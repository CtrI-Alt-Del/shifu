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

    if (
      response.statusCode === 0 ||
      response.statusCode === 429 ||
      response.statusCode >= 500
    ) {
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
  }
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === 'object' && value !== null
}
