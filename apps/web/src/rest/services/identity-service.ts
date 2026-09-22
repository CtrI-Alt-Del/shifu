import type { RestClient } from '@/core/shared/interfaces/rest-client'

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
  return {
    async validateCredentials(
      email: string,
      password: string,
    ): Promise<IdentityAuthentication> {
      const response = await restClient.post<IdentityAuthentication>(
        '/identity/sign-in',
        { email, password },
      )

      if (response.isFailure) response.throwError()

      return response.body
    },

    async getCurrentSession(accessToken: string): Promise<CurrentIdentitySession> {
      const response = await restClient.get<CurrentIdentitySession>('/identity/session', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })

      if (response.isFailure) response.throwError()
      return response.body
    },

    async publishMainPageEntered(accessToken: string): Promise<void> {
      const response = await restClient.post<void>(
        '/identity/main-page-entries',
        undefined,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()
    },
  }
}
