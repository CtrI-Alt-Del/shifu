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

      if (response.isFailure) response.throwError()
      return response.body
    },

    async getPendingConfirmationStatus(pendingHandle: string) {
      const response = await restClient.post<PendingConfirmationStatus>(
        '/identity/pending-confirmations/status',
        { pending_handle: pendingHandle },
      )

      if (response.isFailure) response.throwError()
      return response.body
    },

    async resendConfirmation(pendingHandle: string) {
      const response = await restClient.post<ResendConfirmationResult>(
        '/identity/pending-confirmations/resend',
        { pending_handle: pendingHandle },
      )

      if (response.isFailure) response.throwError()
      return response.body
    },

    async confirmEmail(token: string) {
      const response = await restClient.post<EmailConfirmationResult>(
        '/identity/email-confirmations',
        { token },
      )

      if (response.isFailure) response.throwError()
      return response.body
    },
  }
}
