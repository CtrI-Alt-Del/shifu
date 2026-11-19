import type { BrowserPushNotificationSubscription } from '@/core/communication/browser-push-notification'
import type { StreakReminderPreference } from '@/core/communication/streak-reminder-preference'
import type { RestClient } from '@/core/shared/interfaces/rest-client'

export type CommunicationService = ReturnType<typeof CommunicationService>

export const CommunicationService = (restClient: RestClient) => {
  return {
    async getPushPublicKey(accessToken: string): Promise<{ publicKey: string }> {
      const response = await restClient.get<{ publicKey: string }>(
        '/communication/push-subscriptions/public-key',
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },

    async registerPushSubscription(
      accessToken: string,
      subscription: BrowserPushNotificationSubscription,
    ): Promise<void> {
      const response = await restClient.put<undefined>(
        '/communication/push-subscriptions',
        subscription,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
    },

    async getStreakReminderPreference(
      accessToken: string,
    ): Promise<StreakReminderPreference> {
      const response = await restClient.get<StreakReminderPreference>(
        '/communication/streak-reminder-preference',
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },

    async changeStreakReminderPreference(
      accessToken: string,
      enabled: boolean,
    ): Promise<StreakReminderPreference> {
      const response = await restClient.put<StreakReminderPreference>(
        '/communication/streak-reminder-preference',
        { enabled },
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },
  }
}
