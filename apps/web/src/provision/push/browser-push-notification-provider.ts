import type {
  BrowserPushNotificationPermission,
  BrowserPushNotificationProvider as IBrowserPushNotificationProvider,
  BrowserPushNotificationSubscription,
} from '@/core/communication/browser-push-notification'
import { AppError } from '@/core/errors/app-error'

const SERVICE_WORKER_URL = '/sw.js'
const SERVICE_WORKER_SCOPE = '/'

export const BrowserPushNotificationProvider = (): IBrowserPushNotificationProvider => {
  function isSupported(): boolean {
    return (
      typeof window !== 'undefined' &&
      'Notification' in window &&
      'serviceWorker' in navigator &&
      'PushManager' in window
    )
  }

  function decodePublicKey(publicKey: string): Uint8Array<ArrayBuffer> {
    const padding = '='.repeat((4 - (publicKey.length % 4)) % 4)
    const base64 = `${publicKey}${padding}`.replace(/-/g, '+').replace(/_/g, '/')
    const decoded = window.atob(base64)
    const bytes = new Uint8Array(new ArrayBuffer(decoded.length))
    for (let index = 0; index < decoded.length; index += 1) {
      bytes[index] = decoded.charCodeAt(index)
    }
    return bytes
  }

  function usesApplicationServerKey(
    subscription: PushSubscription,
    applicationServerKey: Uint8Array,
  ): boolean {
    const currentKey = subscription.options.applicationServerKey
    // A browser that does not expose the key leaves nothing to compare, so the
    // subscription is kept.
    if (!currentKey) return true

    const currentBytes = new Uint8Array(currentKey)
    return (
      currentBytes.length === applicationServerKey.length &&
      currentBytes.every((byte, index) => byte === applicationServerKey[index])
    )
  }

  function toSubscription(
    subscription: PushSubscription,
  ): BrowserPushNotificationSubscription {
    const { endpoint, keys } = subscription.toJSON()
    if (!endpoint || !keys?.p256dh || !keys.auth) {
      throw new AppError(
        'Este navegador não devolveu os dados da inscrição de notificações.',
        'Erro de notificações',
      )
    }
    return { endpoint, keys: { p256dh: keys.p256dh, auth: keys.auth } }
  }

  return {
    getPermission(): BrowserPushNotificationPermission {
      if (!isSupported()) return 'unsupported'
      return Notification.permission
    },

    async requestPermission(): Promise<BrowserPushNotificationPermission> {
      if (!isSupported()) return 'unsupported'
      return Notification.requestPermission()
    },

    async subscribe(publicKey: string): Promise<BrowserPushNotificationSubscription> {
      if (!isSupported()) {
        throw new AppError(
          'Este navegador não recebe notificações.',
          'Erro de notificações',
        )
      }
      await navigator.serviceWorker.register(SERVICE_WORKER_URL, {
        scope: SERVICE_WORKER_SCOPE,
      })
      const registration = await navigator.serviceWorker.ready
      const applicationServerKey = decodePublicKey(publicKey)
      const existing = await registration.pushManager.getSubscription()
      if (existing && usesApplicationServerKey(existing, applicationServerKey))
        return toSubscription(existing)

      // A subscription made for another key can never receive this server's pushes.
      if (existing) await existing.unsubscribe()

      const created = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey,
      })
      return toSubscription(created)
    },

    async getSubscription(): Promise<BrowserPushNotificationSubscription | null> {
      if (!isSupported()) return null
      const registration =
        await navigator.serviceWorker.getRegistration(SERVICE_WORKER_SCOPE)
      const subscription = await registration?.pushManager.getSubscription()
      return subscription ? toSubscription(subscription) : null
    },
  }
}
