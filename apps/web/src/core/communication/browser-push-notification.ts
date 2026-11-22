export type BrowserPushNotificationPermission =
  | 'unsupported'
  | 'default'
  | 'granted'
  | 'denied'

export type BrowserPushNotificationSubscription = {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

export interface BrowserPushNotificationProvider {
  getPermission(): BrowserPushNotificationPermission
  requestPermission(): Promise<BrowserPushNotificationPermission>
  subscribe(publicKey: string): Promise<BrowserPushNotificationSubscription>
  getSubscription(): Promise<BrowserPushNotificationSubscription | null>
}
