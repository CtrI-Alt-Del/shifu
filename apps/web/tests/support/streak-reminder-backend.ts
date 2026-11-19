import type { Page, Request, Route } from '@playwright/test'

import { serverFnExport, serverFnInput } from './mentor-memories-backend'

/**
 * Controlled backend and browser push stub for the streak reminder suites. It
 * answers the BFF server functions with the post-mapping shapes the web layer
 * consumes and replaces `Notification`, `PushManager` and `navigator.serviceWorker`,
 * so it proves rendered contracts and the outgoing request order, not real
 * delivery or persistence.
 */
export type InviteStatus = 'not-eligible' | 'pending' | 'answered'

export type PushStubOptions = {
  supported?: boolean
  permission?: 'default' | 'granted' | 'denied'
  requestResult?: 'default' | 'granted' | 'denied'
  // A subscription the browser already holds: made for the server's key or for another one.
  existingSubscription?: 'none' | 'current-key' | 'other-key'
}

export type StreakReminderBackendOptions = {
  inviteStatus?: InviteStatus
  hour?: number
  enabled?: boolean
  hourFailure?: boolean
  preferenceReadFailure?: boolean
  push?: PushStubOptions
}

export type BackendCall = {
  name: string
  data: Record<string, unknown>
}

const PUSH_PUBLIC_KEY = 'AQIDBAUGBwgJCg'

const SERVER_FUNCTIONS = {
  getStreakReminder: 'reminder-read',
  answerStreakReminderInvite: 'answer',
  getPushPublicKey: 'public-key',
  registerPushSubscription: 'subscription',
  changeStreakReminderPreference: 'preference',
  getStreakReminderPreference: 'preference-read',
  changeStreakReminderHour: 'hour',
} as const

export const STUB_SUBSCRIPTION = {
  endpoint: 'https://push.example.test/send/playwright',
  keys: { p256dh: 'playwright-p256dh', auth: 'playwright-auth' },
}

function applyPushStub(options: Required<PushStubOptions>) {
  const target = window as unknown as Record<string, unknown>
  const calls: string[] = []
  target.__pushStubCalls = calls
  if (!options.supported) {
    Reflect.deleteProperty(target, 'Notification')
    Reflect.deleteProperty(target, 'PushManager')
    return
  }

  let permission = options.permission
  class StubNotification {
    static get permission() {
      return permission
    }
    static requestPermission() {
      calls.push('requestPermission')
      permission = options.requestResult
      return Promise.resolve(permission)
    }
  }
  target.Notification = StubNotification
  target.PushManager = class PushManager {}

  const subscription = {
    toJSON: () => ({
      endpoint: 'https://push.example.test/send/playwright',
      keys: { p256dh: 'playwright-p256dh', auth: 'playwright-auth' },
    }),
  }
  const currentKey = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).buffer
  const otherKey = new Uint8Array([9, 9, 9, 9, 9, 9, 9, 9, 9, 9]).buffer
  const existingSubscription = {
    ...subscription,
    options: {
      applicationServerKey:
        options.existingSubscription === 'other-key' ? otherKey : currentKey,
    },
    unsubscribe: async () => {
      calls.push('unsubscribe')
      current = null
      return true
    },
  }
  let current: typeof existingSubscription | null =
    options.existingSubscription === 'current-key' ||
    options.existingSubscription === 'other-key'
      ? existingSubscription
      : null
  const registration = {
    pushManager: {
      getSubscription: async () => current,
      subscribe: async () => {
        calls.push('subscribe')
        current = {
          ...existingSubscription,
          options: { applicationServerKey: currentKey },
        }
        return current
      },
    },
  }
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: {
      register: async (url: string) => {
        calls.push(`register ${url}`)
        return registration
      },
      ready: Promise.resolve(registration),
      getRegistration: async () => registration,
    },
  })
}

export async function installBrowserPushStub(page: Page, stub: PushStubOptions = {}) {
  const options: Required<PushStubOptions> = {
    supported: stub.supported ?? true,
    permission: stub.permission ?? 'default',
    requestResult: stub.requestResult ?? 'granted',
    existingSubscription: stub.existingSubscription ?? 'none',
  }
  // The authenticated fixture is already loaded, so the stub applies to the current
  // document as well as to every later navigation.
  await page.addInitScript(applyPushStub, options)
  await page.evaluate(applyPushStub, options)
}

export function pushStubCalls(page: Page): Promise<string[]> {
  return page.evaluate(
    () => (window as unknown as { __pushStubCalls?: string[] }).__pushStubCalls ?? [],
  )
}

// The shared decoder maps every seroval constant to undefined, which loses booleans.
// Other suites rely on that behavior, so the reminder scenarios decode their own
// body: seroval constants are 0 null, 1 undefined, 2 true and 3 false.
function decodeSeroval(value: unknown): unknown {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return value
  const node = value as { t?: unknown; s?: unknown; p?: { k?: unknown; v?: unknown } }
  if (node.t === 0 || node.t === 1) return node.s
  if (node.t === 2) return [null, undefined, true, false][node.s as number]
  if (node.t === 10 && Array.isArray(node.p?.k) && Array.isArray(node.p?.v)) {
    const values = node.p.v
    return Object.fromEntries(
      node.p.k.map((key, index) => [String(key), decodeSeroval(values[index])]),
    )
  }
  return value
}

function streakReminderInput(request: Request): Record<string, unknown> {
  const body = request.postData()
  if (body) {
    try {
      const decoded = decodeSeroval((JSON.parse(body) as { t?: unknown }).t)
      if (typeof decoded === 'object' && decoded !== null) {
        const record = decoded as Record<string, unknown>
        const nested = record.data
        const input =
          typeof nested === 'object' && nested !== null
            ? (nested as Record<string, unknown>)
            : record
        if (Object.keys(input).length) return input
      }
    } catch {
      // GET server functions carry their input in the URL instead.
    }
  }
  return serverFnInput(request)
}

export async function installStreakReminderBackend(
  page: Page,
  options: StreakReminderBackendOptions = {},
) {
  const state = {
    inviteStatus: options.inviteStatus ?? ('answered' as InviteStatus),
    hour: options.hour ?? 18,
    enabled: options.enabled ?? false,
  }
  const calls: BackendCall[] = []

  function fulfill(route: Route, result: unknown, status = 200) {
    return route.fulfill({
      body: JSON.stringify({ result }),
      contentType: 'application/json',
      status,
    })
  }

  await page.route('**/_serverFn/**', async (route) => {
    const request = route.request()
    const exportName = serverFnExport(request.url()) ?? ''
    const entry = Object.entries(SERVER_FUNCTIONS).find(([functionName]) =>
      exportName.startsWith(`${functionName}_`),
    )
    if (!entry) {
      await route.fallback()
      return
    }
    const name = entry[1]
    const data = streakReminderInput(request)
    calls.push({ name, data })

    switch (name) {
      case 'reminder-read':
        await fulfill(route, {
          kind: 'ok',
          streakReminder: { hour: state.hour, inviteStatus: state.inviteStatus },
        })
        return
      case 'answer':
        state.inviteStatus = 'answered'
        await fulfill(route, {
          kind: 'ok',
          streakReminder: { hour: state.hour, inviteStatus: state.inviteStatus },
        })
        return
      case 'public-key':
        await fulfill(route, { kind: 'ok', publicKey: PUSH_PUBLIC_KEY })
        return
      case 'subscription':
        await fulfill(route, { kind: 'ok' })
        return
      case 'preference':
        state.enabled = data.enabled === true
        await fulfill(route, { kind: 'ok', preference: { enabled: state.enabled } })
        return
      case 'preference-read':
        if (options.preferenceReadFailure) {
          await fulfill(route, { kind: 'unavailable' })
          return
        }
        await fulfill(route, { kind: 'ok', preference: { enabled: state.enabled } })
        return
      case 'hour':
        if (options.hourFailure) {
          await fulfill(route, { kind: 'unavailable' })
          return
        }
        state.hour = Number(data.hour)
        await fulfill(route, {
          kind: 'ok',
          streakReminder: { hour: state.hour, inviteStatus: state.inviteStatus },
        })
        return
    }
  })

  return {
    calls,
    state,
    callsNamed: (name: string) => calls.filter((call) => call.name === name),
    // The reads the shell and the card make on their own are left out so a test
    // can assert the order of the learner-driven writes.
    writeOrder: () =>
      calls
        .map((call) => call.name)
        .filter((name) => name !== 'reminder-read' && name !== 'preference-read'),
    recoverPreferenceRead() {
      options.preferenceReadFailure = false
    },
  }
}

export function collectApplicationErrors(page: Page) {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    // Failed resource loads come from unmocked, unrelated requests, not from the
    // application code under test.
    if (
      message.type() === 'error' &&
      !message.text().startsWith('Failed to load resource')
    )
      errors.push(message.text())
  })
  return errors
}
