import { createServerFn } from '@tanstack/react-start'
import { useEffect, useState } from 'react'
import { z } from 'zod'

import type { BrowserPushNotificationPermission } from '@/core/communication/browser-push-notification'
import type { ServerFunctionFailure } from '@/core/shared/responses/server-function-failure'
import { runStreakReminderRequest } from '@/provision/push/streak-reminder-server-provider'
import { BrowserPushNotificationProvider } from '@/provision/push/browser-push-notification-provider'

const ACCOUNT_EMAIL = z.string().email()

const REGISTER_PUSH_SUBSCRIPTION_INPUT = z
  .object({
    accountEmail: ACCOUNT_EMAIL,
    endpoint: z.string().url().startsWith('https://').max(2048),
    keys: z
      .object({ p256dh: z.string().min(1).max(255), auth: z.string().min(1).max(255) })
      .strict(),
  })
  .strict()

export type GetPushPublicKeyResult =
  | { kind: 'ok'; publicKey: string }
  | ServerFunctionFailure

export type RegisterPushSubscriptionResult = { kind: 'ok' } | ServerFunctionFailure

export type BrowserPushNotificationEnrollmentOutcome =
  | 'enrolled'
  | 'blocked'
  | 'dismissed'
  | 'unsupported'
  | 'failed'

export const getPushPublicKey = createServerFn({ method: 'GET' }).handler(
  async (): Promise<GetPushPublicKeyResult> => {
    const result = await runStreakReminderRequest(
      null,
      ({ accessToken, communicationService }) =>
        communicationService.getPushPublicKey(accessToken),
    )
    if (result.kind === 'ok') return { kind: 'ok', publicKey: result.value.publicKey }
    return result
  },
)

export const registerPushSubscription = createServerFn({ method: 'POST' })
  .validator((data: unknown) => REGISTER_PUSH_SUBSCRIPTION_INPUT.parse(data))
  .handler(async ({ data }): Promise<RegisterPushSubscriptionResult> => {
    const { accountEmail, endpoint, keys } = data
    const result = await runStreakReminderRequest(
      accountEmail,
      ({ accessToken, communicationService }) =>
        communicationService.registerPushSubscription(accessToken, { endpoint, keys }),
    )
    return result.kind === 'ok' ? { kind: 'ok' } : result
  })

export function useBrowserPushNotificationEnrollment(accountEmail: string) {
  const [provider] = useState(() => BrowserPushNotificationProvider())
  const [permission, setPermission] = useState<BrowserPushNotificationPermission>(() =>
    provider.getPermission(),
  )

  useEffect(() => {
    setPermission(provider.getPermission())
  }, [provider])

  async function subscribeAndRegister(): Promise<boolean> {
    const publicKeyResult = await getPushPublicKey()
    if (publicKeyResult.kind !== 'ok') return false

    const subscription = await provider.subscribe(publicKeyResult.publicKey)
    const registration = await registerPushSubscription({
      data: { accountEmail, ...subscription },
    })
    return registration.kind === 'ok'
  }

  async function enrollThisBrowser(): Promise<BrowserPushNotificationEnrollmentOutcome> {
    const currentPermission = provider.getPermission()
    setPermission(currentPermission)
    if (currentPermission === 'unsupported') return 'unsupported'
    if (currentPermission === 'denied') return 'blocked'

    try {
      const answeredPermission =
        currentPermission === 'granted' ? 'granted' : await provider.requestPermission()
      setPermission(answeredPermission)
      if (answeredPermission === 'unsupported') return 'unsupported'
      if (answeredPermission === 'denied') return 'blocked'
      if (answeredPermission === 'default') return 'dismissed'

      return (await subscribeAndRegister()) ? 'enrolled' : 'failed'
    } catch {
      return 'failed'
    }
  }

  async function refreshThisBrowser(): Promise<void> {
    if (provider.getPermission() !== 'granted') return

    try {
      await subscribeAndRegister()
    } catch {
      return
    }
  }

  return { permission, enrollThisBrowser, refreshThisBrowser }
}
