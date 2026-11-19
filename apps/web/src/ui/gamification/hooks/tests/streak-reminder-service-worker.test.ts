import { readFileSync } from 'node:fs'
import { URL as NodeUrl, fileURLToPath } from 'node:url'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// `public/sw.js` is the receiving half of `useBrowserPushNotificationEnrollment`,
// which registers it. It has no test category of its own in the test-integrity
// rules, so its behavior is proven here, at the hook boundary that owns it, by
// running the real script against a fake service worker global.
const ORIGIN = 'https://shifu.test'
const SERVICE_WORKER_SOURCE = readFileSync(
  fileURLToPath(new NodeUrl('../../../../../public/sw.js', import.meta.url)),
  'utf-8',
)

type Listener = (event: Record<string, unknown>) => void

type FakeClient = {
  url: string
  focus: ReturnType<typeof vi.fn>
  navigate: ReturnType<typeof vi.fn>
}

function createClient(url: string): FakeClient {
  const client: FakeClient = {
    url,
    focus: vi.fn(),
    navigate: vi.fn(async () => client),
  }
  client.focus.mockImplementation(async () => client)
  return client
}

function createWorker(windowClients: FakeClient[] = []) {
  const listeners = new Map<string, Listener>()
  const showNotification = vi.fn(async () => undefined)
  const scope = {
    location: { origin: ORIGIN },
    registration: { showNotification },
    skipWaiting: vi.fn(),
    clients: {
      claim: vi.fn(async () => undefined),
      matchAll: vi.fn(async () => windowClients),
      openWindow: vi.fn(async () => null),
    },
    addEventListener: (type: string, listener: Listener) => listeners.set(type, listener),
  }
  new Function('self', SERVICE_WORKER_SOURCE)(scope)

  async function dispatch(type: string, extra: Record<string, unknown> = {}) {
    const waits: Promise<unknown>[] = []
    listeners.get(type)?.({
      waitUntil: (work: Promise<unknown>) => waits.push(work),
      ...extra,
    })
    await Promise.all(waits)
  }

  function push(data: unknown) {
    return dispatch('push', { data })
  }

  function click(url: unknown) {
    const notification = { close: vi.fn(), data: url === undefined ? undefined : { url } }
    return dispatch('notificationclick', { notification }).then(() => notification)
  }

  return { scope, showNotification, dispatch, push, click }
}

function pushData(value: unknown) {
  return { json: () => value }
}

describe('streak reminder service worker', () => {
  let worker: ReturnType<typeof createWorker>

  beforeEach(() => {
    worker = createWorker()
  })

  it('takes control of the page right after it is registered', async () => {
    await worker.dispatch('install')
    await worker.dispatch('activate')

    expect(worker.scope.skipWaiting).toHaveBeenCalledOnce()
    expect(worker.scope.clients.claim).toHaveBeenCalledOnce()
  })

  it('shows the notification described by a valid push', async () => {
    await worker.push(
      pushData({
        title: 'Shifu',
        body: 'Sua sequência de 7 dias termina hoje — pratique para mantê-la',
        url: '/',
        tag: 'shifu-streak-reminder',
      }),
    )

    expect(worker.showNotification).toHaveBeenCalledWith('Shifu', {
      body: 'Sua sequência de 7 dias termina hoje — pratique para mantê-la',
      tag: 'shifu-streak-reminder',
      icon: '/favicon.svg',
      data: { url: '/' },
    })
  })

  it.each([
    [
      'malformed JSON',
      {
        json: () => {
          throw new SyntaxError('bad json')
        },
      },
    ],
    ['a null payload', pushData(null)],
    ['an array payload', pushData(['Shifu'])],
    ['a string payload', pushData('Shifu')],
    ['a number payload', pushData(7)],
    ['a missing payload', null],
    ['an empty object', pushData({})],
    ['fields of the wrong type', pushData({ title: 3, body: {}, url: false, tag: [] })],
  ])(
    'shows the safe default notification for %s without throwing',
    async (_case, data) => {
      await expect(worker.push(data)).resolves.toBeUndefined()

      expect(worker.showNotification).toHaveBeenCalledOnce()
      expect(worker.showNotification).toHaveBeenCalledWith('Shifu', {
        body: undefined,
        tag: undefined,
        icon: '/favicon.svg',
        data: { url: '/' },
      })
    },
  )

  it('closes the notification and focuses then navigates an existing same-origin tab', async () => {
    const client = createClient(`${ORIGIN}/gamification`)
    worker = createWorker([createClient('https://other.test/'), client])

    const notification = await worker.click('/')

    expect(notification.close).toHaveBeenCalledOnce()
    expect(client.focus).toHaveBeenCalledOnce()
    expect(client.navigate).toHaveBeenCalledWith(`${ORIGIN}/`)
    expect(worker.scope.clients.openWindow).not.toHaveBeenCalled()
  })

  it('opens a window when navigating the tab is rejected', async () => {
    const client = createClient(`${ORIGIN}/`)
    client.navigate.mockRejectedValue(new TypeError('uncontrolled client'))
    worker = createWorker([client])

    await worker.click('/')

    expect(client.navigate).toHaveBeenCalledOnce()
    expect(worker.scope.clients.openWindow).toHaveBeenCalledWith(`${ORIGIN}/`)
  })

  it('opens a window when focusing the tab is rejected', async () => {
    const client = createClient(`${ORIGIN}/`)
    client.focus.mockRejectedValue(new Error('no focus'))
    worker = createWorker([client])

    await worker.click('/')

    expect(worker.scope.clients.openWindow).toHaveBeenCalledWith(`${ORIGIN}/`)
  })

  it('opens a window when no same-origin tab exists', async () => {
    worker = createWorker([createClient('https://other.test/')])

    await worker.click('/')

    expect(worker.scope.clients.openWindow).toHaveBeenCalledWith(`${ORIGIN}/`)
  })

  it('opens a window when there are no tabs at all', async () => {
    await worker.click('/')

    expect(worker.scope.clients.openWindow).toHaveBeenCalledWith(`${ORIGIN}/`)
  })

  it.each([
    ['a foreign origin', 'https://evil.test/steal'],
    ['an invalid address', 'http://'],
    ['a missing address', undefined],
  ])('falls back to the root for %s', async (_case, url) => {
    await worker.click(url)

    expect(worker.scope.clients.openWindow).toHaveBeenCalledWith(`${ORIGIN}/`)
  })
})
