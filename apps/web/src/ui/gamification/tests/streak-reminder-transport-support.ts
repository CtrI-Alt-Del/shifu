import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import axios from 'axios'
import { createElement, type PropsWithChildren } from 'react'
import { vi } from 'vitest'

import type { BrowserPushNotificationProvider } from '@/core/communication/browser-push-notification'

export type RecordedRequest = { method: string; url: string; body: unknown }

export type TransportResponse = { status: number; body?: unknown }

export const BROWSER_SUBSCRIPTION = {
  endpoint: 'https://fcm.googleapis.com/fcm/send/abc',
  keys: { p256dh: 'p256dh-key', auth: 'auth-secret' },
}

// Keeps the consuming hooks, server functions, services, request factory and Axios
// mapping real. Only the network adapter answers, one response per request.
export function installStreakReminderTransport(
  respond: (request: RecordedRequest) => TransportResponse | Promise<TransportResponse>,
  log: string[] = [],
) {
  const requests: RecordedRequest[] = []
  const createClient = axios.create.bind(axios)
  vi.spyOn(axios, 'create').mockImplementation((config) =>
    createClient({
      ...config,
      adapter: async (request) => {
        const recorded: RecordedRequest = {
          method: String(request.method).toUpperCase(),
          url: String(request.url),
          body: typeof request.data === 'string' ? JSON.parse(request.data) : undefined,
        }
        requests.push(recorded)
        log.push(`${recorded.method} ${recorded.url}`)
        const { status, body } = await respond(recorded)
        return { data: body, status, statusText: '', headers: {}, config: request }
      },
    }),
  )
  return requests
}

export function createFakeBrowserPushNotificationProvider(calls: string[] = []) {
  const provider = {
    getPermission: vi.fn<BrowserPushNotificationProvider['getPermission']>(
      () => 'default',
    ),
    requestPermission: vi.fn<BrowserPushNotificationProvider['requestPermission']>(
      async () => {
        calls.push('requestPermission')
        return 'granted'
      },
    ),
    subscribe: vi.fn<BrowserPushNotificationProvider['subscribe']>(async () => {
      calls.push('subscribe')
      return BROWSER_SUBSCRIPTION
    }),
    getSubscription: vi.fn<BrowserPushNotificationProvider['getSubscription']>(
      async () => BROWSER_SUBSCRIPTION,
    ),
  }
  return { provider, calls }
}

export function createQueryClientWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  function QueryWrapper({ children }: PropsWithChildren) {
    return createElement(QueryClientProvider, { client }, children)
  }
  return { client, wrapper: QueryWrapper }
}

export function requestLabels(requests: readonly RecordedRequest[]) {
  return requests.map((request) => `${request.method} ${request.url}`)
}
