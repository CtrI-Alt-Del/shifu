import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { StreakReminder } from '@/core/gamification/streak-reminder'
import {
  BROWSER_SUBSCRIPTION,
  createFakeBrowserPushNotificationProvider,
  createQueryClientWrapper,
  installStreakReminderTransport,
  type RecordedRequest,
  type TransportResponse,
} from '@/ui/gamification/tests/streak-reminder-transport-support'
import { showErrorToast } from '@/ui/shared/notifications'

import { useStreakReminderCard } from '../use-streak-reminder-card'

const mocks = vi.hoisted(() => ({
  log: [] as string[],
  fake: null as null | ReturnType<
    typeof import('@/ui/gamification/tests/streak-reminder-transport-support').createFakeBrowserPushNotificationProvider
  >,
}))

vi.mock('@tanstack/react-start', async () => {
  const { createTestServerFn } = await import(
    '@/ui/gamification/tests/transport-test-support'
  )
  return { createServerFn: createTestServerFn }
})
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://web.test/account/profile'),
}))
vi.mock('@tanstack/react-router', () => ({
  useRouteContext: () => ({ email: 'ana@example.com' }),
}))
vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: {
    shifuServerAppUrl: 'http://upstream.test',
    bffSharedSecret: 'server-owned-secret',
  },
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({
    getCurrentAccess: async () => ({
      accessToken: 'learner-access',
      email: 'ana@example.com',
    }),
  }),
}))
vi.mock('@/provision/push/browser-push-notification-provider', () => ({
  BrowserPushNotificationProvider: () => mocks.fake?.provider,
}))
vi.mock('@/ui/shared/notifications', () => ({
  showErrorToast: vi.fn(),
  showInfoToast: vi.fn(),
  showWarningToast: vi.fn(),
}))

const showErrorToastMock = vi.mocked(showErrorToast)

type Answers = Partial<
  Record<string, TransportResponse | (() => Promise<TransportResponse>)>
>

let streakReminder: StreakReminder
let enabled: boolean
let answers: Answers

const GET_REMINDER = 'GET /gamification/streak-reminder'
const GET_PREFERENCE = 'GET /communication/streak-reminder-preference'
const PUT_PREFERENCE = 'PUT /communication/streak-reminder-preference'
const PUT_HOUR = 'PUT /gamification/streak-reminder/hour'

async function respond(request: RecordedRequest): Promise<TransportResponse> {
  const label = `${request.method} ${request.url}`
  const override = answers[label]
  if (typeof override === 'function') return override()
  if (override) return override
  switch (label) {
    case GET_REMINDER:
      return { status: 200, body: streakReminder }
    case GET_PREFERENCE:
      return { status: 200, body: { enabled } }
    case PUT_PREFERENCE:
      enabled = (request.body as { enabled: boolean }).enabled
      return { status: 200, body: { enabled } }
    case 'GET /communication/push-subscriptions/public-key':
      return { status: 200, body: { publicKey: 'public-key' } }
    case 'PUT /communication/push-subscriptions':
      return { status: 204 }
    case PUT_HOUR:
      streakReminder = {
        ...streakReminder,
        hour: (request.body as { hour: number }).hour,
      }
      return { status: 200, body: streakReminder }
    default:
      return { status: 404 }
  }
}

function deferred() {
  let release: (response: TransportResponse) => void = () => undefined
  const promise = new Promise<TransportResponse>((resolve) => {
    release = resolve
  })
  return { promise, release }
}

async function renderReadyCard() {
  const { client, wrapper } = createQueryClientWrapper()
  const rendered = renderHook(() => useStreakReminderCard(), { wrapper })
  await waitFor(() => expect(rendered.result.current.isLoading).toBe(false))
  return { ...rendered, client }
}

describe('useStreakReminderCard', () => {
  beforeEach(() => {
    mocks.log = []
    mocks.fake = createFakeBrowserPushNotificationProvider(mocks.log)
    streakReminder = { hour: 18, inviteStatus: 'answered' }
    enabled = false
    answers = {}
    showErrorToastMock.mockClear()
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('is loading until both reads answer, then exposes the stored values', async () => {
    enabled = true
    installStreakReminderTransport(respond, mocks.log)
    const { client, wrapper } = createQueryClientWrapper()
    const { result } = renderHook(() => useStreakReminderCard(), { wrapper })

    expect(result.current.isLoading).toBe(true)
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.hour).toBe(18)
    expect(result.current.isEnabled).toBe(true)
    expect(result.current.hasError).toBe(false)
    expect(result.current.notice).toBeNull()
    expect(result.current.isSwitching).toBe(false)
    expect(result.current.isHourPending).toBe(false)
    expect(client.getQueryData(['communication', 'streak-reminder-preference'])).toEqual({
      enabled: true,
    })
  })

  it.each([
    ['denied', 'blocked'],
    ['unsupported', 'unsupported'],
    ['granted', null],
    ['default', null],
  ] as const)('selects the %s permission notice as %s', async (permission, notice) => {
    mocks.fake?.provider.getPermission.mockReturnValue(permission)
    installStreakReminderTransport(respond, mocks.log)

    const { result } = await renderReadyCard()

    expect(result.current.notice).toBe(notice)
  })

  it('reports an error when a read fails and reads both again on retry', async () => {
    answers[GET_PREFERENCE] = { status: 503 }
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()
    expect(result.current.hasError).toBe(true)

    answers[GET_PREFERENCE] = undefined
    act(() => result.current.handleRetry())

    await waitFor(() => expect(result.current.hasError).toBe(false))
    expect(
      requests.filter((request) => request.url === '/gamification/streak-reminder'),
    ).toHaveLength(2)
  })

  it('enrolls this browser and then turns the preference on', async () => {
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()
    mocks.log.length = 0

    await act(async () => {
      await result.current.handleSwitchChange(true)
    })

    expect(mocks.log).toEqual([
      'requestPermission',
      'GET /communication/push-subscriptions/public-key',
      'subscribe',
      'PUT /communication/push-subscriptions',
      PUT_PREFERENCE,
    ])
    expect(
      requests.find((request) => request.url.endsWith('/push-subscriptions'))?.body,
    ).toEqual(BROWSER_SUBSCRIPTION)
    expect(result.current.isEnabled).toBe(true)
    expect(result.current.isSwitching).toBe(false)
  })

  it('turns the preference on even when notifications are blocked in this browser', async () => {
    mocks.fake?.provider.getPermission.mockReturnValue('denied')
    installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()
    mocks.log.length = 0

    await act(async () => {
      await result.current.handleSwitchChange(true)
    })

    expect(mocks.log).toEqual([PUT_PREFERENCE])
    expect(result.current.isEnabled).toBe(true)
    expect(result.current.notice).toBe('blocked')
  })

  it('turns the preference on without enrolling when the browser is unsupported', async () => {
    mocks.fake?.provider.getPermission.mockReturnValue('unsupported')
    installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()
    mocks.log.length = 0

    await act(async () => {
      await result.current.handleSwitchChange(true)
    })

    expect(mocks.log).toEqual([PUT_PREFERENCE])
    expect(result.current.notice).toBe('unsupported')
  })

  it('turns the preference on when the permission prompt is dismissed', async () => {
    mocks.fake?.provider.requestPermission.mockResolvedValue('default')
    installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()
    mocks.log.length = 0

    await act(async () => {
      await result.current.handleSwitchChange(true)
    })

    expect(mocks.log).toEqual([PUT_PREFERENCE])
    expect(result.current.isEnabled).toBe(true)
  })

  it('keeps the preference off and reports a toast when enrolling fails', async () => {
    answers['GET /communication/push-subscriptions/public-key'] = { status: 503 }
    installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()

    await act(async () => {
      await result.current.handleSwitchChange(true)
    })

    expect(showErrorToastMock).toHaveBeenCalledOnce()
    expect(mocks.log).not.toContain(PUT_PREFERENCE)
    expect(result.current.isEnabled).toBe(false)
    expect(result.current.isSwitching).toBe(false)
  })

  it('reports a toast and keeps the switch when saving the preference fails', async () => {
    answers[PUT_PREFERENCE] = { status: 503 }
    installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()

    await act(async () => {
      await result.current.handleSwitchChange(true)
    })

    expect(showErrorToastMock).toHaveBeenCalledOnce()
    expect(result.current.isEnabled).toBe(false)
    expect(result.current.isSwitching).toBe(false)
  })

  it('turns the preference off without touching the browser', async () => {
    enabled = true
    installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()
    mocks.log.length = 0

    await act(async () => {
      await result.current.handleSwitchChange(false)
    })

    expect(mocks.log).toEqual([PUT_PREFERENCE])
    expect(mocks.fake?.provider.requestPermission).not.toHaveBeenCalled()
    expect(result.current.isEnabled).toBe(false)
  })

  it('marks the switch pending and ignores a second change while saving', async () => {
    const pending = deferred()
    answers[PUT_PREFERENCE] = () => pending.promise
    const requests = installStreakReminderTransport(respond, mocks.log)
    mocks.fake?.provider.getPermission.mockReturnValue('denied')
    const { result } = await renderReadyCard()

    let firstChange: Promise<void> = Promise.resolve()
    act(() => {
      firstChange = result.current.handleSwitchChange(true)
    })
    await waitFor(() => expect(result.current.isSwitching).toBe(true))
    await act(async () => {
      await result.current.handleSwitchChange(false)
    })
    expect(
      requests.filter(
        (request) => request.url.endsWith('-preference') && request.method === 'PUT',
      ),
    ).toHaveLength(1)

    await act(async () => {
      pending.release({ status: 200, body: { enabled: true } })
      await firstChange
    })
    expect(result.current.isSwitching).toBe(false)
    expect(result.current.isEnabled).toBe(true)
  })

  it('saves a selected hour at once and shows it while saving', async () => {
    const pending = deferred()
    answers[PUT_HOUR] = () => pending.promise
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()

    let change: Promise<void> = Promise.resolve()
    act(() => {
      change = result.current.handleHourChange('20')
    })
    await waitFor(() => expect(result.current.isHourPending).toBe(true))
    expect(result.current.hour).toBe(20)
    await act(async () => {
      await result.current.handleHourChange('21')
    })
    expect(requests.filter((request) => request.url.endsWith('/hour'))).toHaveLength(1)

    await act(async () => {
      pending.release({ status: 200, body: { hour: 20, inviteStatus: 'answered' } })
      await change
    })
    expect(requests.find((request) => request.url.endsWith('/hour'))?.body).toEqual({
      hour: 20,
    })
    expect(result.current.isHourPending).toBe(false)
    expect(result.current.hour).toBe(20)
  })

  it('reverts to the stored hour and reports a toast when saving fails', async () => {
    answers[PUT_HOUR] = { status: 503 }
    installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()

    await act(async () => {
      await result.current.handleHourChange('20')
    })

    expect(result.current.hour).toBe(18)
    expect(result.current.isHourPending).toBe(false)
    expect(showErrorToastMock).toHaveBeenCalledOnce()
  })

  it('ignores an empty or unchanged hour selection', async () => {
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()

    await act(async () => {
      await result.current.handleHourChange(null)
      await result.current.handleHourChange('18')
    })

    expect(requests.some((request) => request.url.endsWith('/hour'))).toBe(false)
  })

  it('silently refreshes this browser once when enabled and allowed', async () => {
    enabled = true
    mocks.fake?.provider.getPermission.mockReturnValue('granted')
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result, rerender } = await renderReadyCard()

    await waitFor(() =>
      expect(
        requests.some((request) => request.url === '/communication/push-subscriptions'),
      ).toBe(true),
    )
    rerender()
    await act(async () => {
      await result.current.handleHourChange('19')
    })

    expect(mocks.fake?.provider.subscribe).toHaveBeenCalledTimes(1)
    expect(
      requests.filter((request) => request.url === '/communication/push-subscriptions'),
    ).toHaveLength(1)
    expect(showErrorToastMock).not.toHaveBeenCalled()
  })

  it('does not refresh this browser again when the switch is turned on after mount', async () => {
    mocks.fake?.provider.getPermission.mockReturnValue('granted')
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result } = await renderReadyCard()

    await act(async () => {
      await result.current.handleSwitchChange(true)
    })

    expect(
      requests.filter((request) => request.url === '/communication/push-subscriptions'),
    ).toHaveLength(1)
    expect(mocks.fake?.provider.subscribe).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['the preference is off', false, 'granted'],
    ['permission is not granted', true, 'default'],
  ] as const)(
    'does not refresh this browser when %s',
    async (_reason, isEnabled, permission) => {
      enabled = isEnabled
      mocks.fake?.provider.getPermission.mockReturnValue(permission)
      installStreakReminderTransport(respond, mocks.log)

      await renderReadyCard()

      expect(mocks.fake?.provider.subscribe).not.toHaveBeenCalled()
    },
  )

  it('keeps quiet when the silent refresh fails', async () => {
    enabled = true
    mocks.fake?.provider.getPermission.mockReturnValue('granted')
    mocks.fake?.provider.subscribe.mockRejectedValue(new Error('push service down'))
    installStreakReminderTransport(respond, mocks.log)

    await renderReadyCard()

    await waitFor(() => expect(mocks.fake?.provider.subscribe).toHaveBeenCalledOnce())
    expect(showErrorToastMock).not.toHaveBeenCalled()
  })
})
