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
import { showErrorToast, showInfoToast } from '@/ui/shared/notifications'

import { useStreakReminderInvite } from '../use-streak-reminder-invite'

const mocks = vi.hoisted(() => ({
  pathname: '/',
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
  getRequest: () => new Request('http://web.test/'),
}))
vi.mock('@tanstack/react-router', () => ({
  useLocation: () => ({ pathname: mocks.pathname }),
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
const showInfoToastMock = vi.mocked(showInfoToast)

type Answers = Partial<Record<string, TransportResponse>>

let streakReminder: StreakReminder
let answers: Answers

function respond(request: RecordedRequest): TransportResponse {
  const label = `${request.method} ${request.url}`
  const override = answers[label]
  if (override) return override
  switch (label) {
    case 'GET /gamification/streak-reminder':
      return { status: 200, body: streakReminder }
    case 'POST /gamification/streak-reminder/invite-answer':
      streakReminder = { ...streakReminder, inviteStatus: 'answered' }
      return { status: 200, body: streakReminder }
    case 'GET /communication/push-subscriptions/public-key':
      return { status: 200, body: { publicKey: 'public-key' } }
    case 'PUT /communication/push-subscriptions':
      return { status: 204 }
    case 'PUT /communication/streak-reminder-preference':
      return { status: 200, body: request.body }
    case 'PUT /gamification/streak-reminder/hour':
      return {
        status: 200,
        body: { ...streakReminder, hour: (request.body as { hour: number }).hour },
      }
    default:
      return { status: 404 }
  }
}

function renderInvite() {
  const { client, wrapper } = createQueryClientWrapper()
  const rendered = renderHook(
    () => useStreakReminderInvite({ accountEmail: 'ana@example.com' }),
    {
      wrapper,
    },
  )
  return { ...rendered, client }
}

describe('useStreakReminderInvite', () => {
  beforeEach(() => {
    mocks.pathname = '/'
    mocks.log = []
    mocks.fake = createFakeBrowserPushNotificationProvider(mocks.log)
    streakReminder = { hour: 18, inviteStatus: 'pending' }
    answers = {}
    showErrorToastMock.mockClear()
    showInfoToastMock.mockClear()
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it.each(['not-eligible', 'answered'] as const)(
    'stays closed when the invite status is %s',
    async (inviteStatus) => {
      streakReminder = { hour: 18, inviteStatus }
      const requests = installStreakReminderTransport(respond, mocks.log)
      const { result } = renderInvite()

      await waitFor(() => expect(requests).toHaveLength(1))
      expect(result.current.isOpen).toBe(false)
    },
  )

  it('stays closed and unanswered in a browser that cannot receive push', async () => {
    mocks.fake?.provider.getPermission.mockReturnValue('unsupported')
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()

    await waitFor(() => expect(requests).toHaveLength(1))
    expect(result.current.isOpen).toBe(false)
    expect(requests.map((request) => request.method)).toEqual(['GET'])
  })

  it('opens on the invite step without asking the browser for permission', async () => {
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()

    await waitFor(() => expect(result.current.isOpen).toBe(true))
    expect(result.current.step).toBe('invite')
    expect(result.current.hour).toBe(18)
    expect(mocks.fake?.provider.requestPermission).not.toHaveBeenCalled()
    expect(mocks.log).toEqual(['GET /gamification/streak-reminder'])
  })

  it('answers and closes on "Agora não" and never reopens', async () => {
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result, rerender, client } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))

    await act(async () => {
      await result.current.handleDecline()
    })

    expect(result.current.isOpen).toBe(false)
    expect(
      requests.filter((request) => request.url.endsWith('/invite-answer')),
    ).toHaveLength(1)
    expect(client.getQueryData(['gamification', 'streak-reminder'])).toEqual({
      hour: 18,
      inviteStatus: 'answered',
    })
    rerender()
    expect(result.current.isOpen).toBe(false)
  })

  it('answers before requesting permission, then enrolls and shows the hour step', async () => {
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result, client } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))

    await act(async () => {
      await result.current.handleEnable()
    })

    expect(mocks.log).toEqual([
      'GET /gamification/streak-reminder',
      'POST /gamification/streak-reminder/invite-answer',
      'requestPermission',
      'GET /communication/push-subscriptions/public-key',
      'subscribe',
      'PUT /communication/push-subscriptions',
      'PUT /communication/streak-reminder-preference',
    ])
    expect(mocks.fake?.provider.subscribe).toHaveBeenCalledWith('public-key')
    expect(
      requests.find((request) => request.url.endsWith('/push-subscriptions'))?.body,
    ).toEqual(BROWSER_SUBSCRIPTION)
    expect(
      requests.find((request) => request.url.endsWith('/streak-reminder-preference'))
        ?.body,
    ).toEqual({ enabled: true })
    expect(client.getQueryData(['communication', 'streak-reminder-preference'])).toEqual({
      enabled: true,
    })
    expect(result.current.isOpen).toBe(true)
    expect(result.current.step).toBe('hour')
    expect(result.current.hour).toBe(18)
    expect(result.current.isEnabling).toBe(false)
  })

  it('saves the chosen hour and closes', async () => {
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result, client } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    await act(async () => {
      await result.current.handleEnable()
    })

    act(() => result.current.handleHourChange('19'))
    expect(result.current.hour).toBe(19)
    await act(async () => {
      await result.current.handleSaveHour()
    })

    expect(requests.at(-1)).toEqual({
      method: 'PUT',
      url: '/gamification/streak-reminder/hour',
      body: { hour: 19 },
    })
    expect(client.getQueryData(['gamification', 'streak-reminder'])).toMatchObject({
      hour: 19,
    })
    expect(result.current.isOpen).toBe(false)
    expect(result.current.isSavingHour).toBe(false)
  })

  it('ignores an empty hour selection', async () => {
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))

    act(() => result.current.handleHourChange(null))

    expect(result.current.hour).toBe(18)
  })

  it('closes on "Pular" without saving the hour', async () => {
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    await act(async () => {
      await result.current.handleEnable()
    })

    act(() => result.current.handleSkip())

    expect(result.current.isOpen).toBe(false)
    expect(requests.some((request) => request.url.endsWith('/hour'))).toBe(false)
  })

  it('keeps the hour step open and reports a toast when saving the hour fails', async () => {
    answers['PUT /gamification/streak-reminder/hour'] = { status: 503 }
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    await act(async () => {
      await result.current.handleEnable()
    })

    await act(async () => {
      await result.current.handleSaveHour()
    })

    expect(result.current.isOpen).toBe(true)
    expect(result.current.step).toBe('hour')
    expect(result.current.isSavingHour).toBe(false)
    expect(showErrorToastMock).toHaveBeenCalledOnce()
  })

  it.each([
    ['blocked', 'denied'],
    ['dismissed', 'default'],
  ] as const)(
    'closes with a toast pointing to Sua conta when the permission is %s',
    async (_outcome, answeredPermission) => {
      mocks.fake?.provider.requestPermission.mockResolvedValue(answeredPermission)
      const requests = installStreakReminderTransport(respond, mocks.log)
      const { result } = renderInvite()
      await waitFor(() => expect(result.current.isOpen).toBe(true))

      await act(async () => {
        await result.current.handleEnable()
      })

      expect(result.current.isOpen).toBe(false)
      expect(showInfoToastMock).toHaveBeenCalledWith(expect.stringContaining('Sua conta'))
      expect(
        requests.some((request) => request.url.includes('/push-subscriptions')),
      ).toBe(false)
    },
  )

  it('shows an error toast and closes when the browser cannot be enrolled', async () => {
    answers['GET /communication/push-subscriptions/public-key'] = { status: 503 }
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))

    await act(async () => {
      await result.current.handleEnable()
    })

    expect(showErrorToastMock).toHaveBeenCalledWith(expect.stringContaining('Sua conta'))
    expect(result.current.isOpen).toBe(false)
  })

  it('shows an error toast and closes when the preference cannot be turned on', async () => {
    answers['PUT /communication/streak-reminder-preference'] = { status: 503 }
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))

    await act(async () => {
      await result.current.handleEnable()
    })

    expect(showErrorToastMock).toHaveBeenCalledOnce()
    expect(result.current.isOpen).toBe(false)
  })

  it('stays open and does not ask for permission when the answer fails', async () => {
    answers['POST /gamification/streak-reminder/invite-answer'] = { status: 503 }
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))

    await act(async () => {
      await result.current.handleEnable()
    })

    expect(showErrorToastMock).toHaveBeenCalledOnce()
    expect(mocks.fake?.provider.requestPermission).not.toHaveBeenCalled()
    expect(result.current.isOpen).toBe(true)
    expect(result.current.isEnabling).toBe(false)
  })

  it('treats closing the invite step like "Agora não"', async () => {
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))

    await act(async () => {
      result.current.handleOpenChange(false)
    })

    await waitFor(() =>
      expect(requests.some((request) => request.url.endsWith('/invite-answer'))).toBe(
        true,
      ),
    )
    expect(result.current.isOpen).toBe(false)
  })

  it('treats closing the hour step like "Pular" and ignores an open request', async () => {
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    await act(async () => {
      await result.current.handleEnable()
    })

    act(() => result.current.handleOpenChange(true))
    expect(result.current.isOpen).toBe(true)
    act(() => result.current.handleOpenChange(false))

    expect(result.current.isOpen).toBe(false)
  })

  it('reads the invite state again when the pathname changes', async () => {
    streakReminder = { hour: 18, inviteStatus: 'not-eligible' }
    const requests = installStreakReminderTransport(respond, mocks.log)
    const { result, rerender } = renderInvite()
    await waitFor(() => expect(requests).toHaveLength(1))
    expect(result.current.isOpen).toBe(false)

    streakReminder = { hour: 18, inviteStatus: 'pending' }
    mocks.pathname = '/gamification'
    rerender()

    await waitFor(() => expect(result.current.isOpen).toBe(true))
    expect(
      requests.filter((request) => request.url === '/gamification/streak-reminder'),
    ).toHaveLength(2)
  })

  it('returns focus to the previously focused element on close', async () => {
    const trigger = document.createElement('button')
    document.body.append(trigger)
    trigger.focus()
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    const event = new Event('focus', { cancelable: true })

    act(() => result.current.handleCloseAutoFocus(event))

    expect(event.defaultPrevented).toBe(true)
    expect(trigger).toHaveFocus()
    trigger.remove()
  })

  it('leaves the default focus behavior when nothing was focused before', async () => {
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    const event = new Event('focus', { cancelable: true })

    act(() => result.current.handleCloseAutoFocus(event))

    expect(event.defaultPrevented).toBe(false)
  })

  it('exposes the select portal container set by the dialog', async () => {
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    const container = document.createElement('div')

    act(() => result.current.setSelectPortalContainer(container))

    expect(result.current.selectPortalContainer).toBe(container)
  })

  it('keeps the default open focus from running so the hook can choose the target', async () => {
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    const event = new Event('focus', { cancelable: true })

    act(() => result.current.handleOpenAutoFocus(event))

    expect(event.defaultPrevented).toBe(true)
  })

  it('focuses the primary action on the invite step and the hour field on the hour step', async () => {
    installStreakReminderTransport(respond, mocks.log)
    const { result } = renderInvite()
    await waitFor(() => expect(result.current.isOpen).toBe(true))
    const container = document.createElement('div')
    const enable = document.createElement('button')
    enable.id = 'streak-reminder-invite-enable'
    const hourField = document.createElement('button')
    hourField.id = 'streak-reminder-invite-hour'
    container.append(enable, hourField)
    document.body.append(container)

    act(() => result.current.setSelectPortalContainer(container))
    expect(enable).toHaveFocus()

    await act(async () => {
      await result.current.handleEnable()
    })
    expect(result.current.step).toBe('hour')
    expect(hourField).toHaveFocus()
    container.remove()
  })
})
