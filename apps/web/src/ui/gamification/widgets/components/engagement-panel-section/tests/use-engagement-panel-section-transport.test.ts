import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { GamificationOverview } from '@/core/gamification/overview'
import {
  getOverview,
  useGamificationOverviewQuery,
} from '@/ui/gamification/hooks/use-gamification-overview-query'
import {
  createQueryWrapper,
  installGamificationTransport,
} from '@/ui/gamification/tests/transport-test-support'

import { useEngagementPanelSection } from '../use-engagement-panel-section'
import { useEngagementSummary } from '../../engagement-summary/use-engagement-summary'

const mocks = vi.hoisted(() => ({ getCurrentAccess: vi.fn() }))

vi.mock('@tanstack/react-start', async () => {
  const { createTestServerFn } = await import(
    '@/ui/gamification/tests/transport-test-support'
  )
  return { createServerFn: createTestServerFn }
})
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://web.test/gamification'),
}))
vi.mock('@/start', () => ({ serverFunctionTelemetryMiddleware: {} }))
vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: {
    shifuServerAppUrl: 'http://upstream.test',
    bffSharedSecret: 'server-owned-secret',
  },
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))

const body: GamificationOverview = {
  level: 4,
  totalXp: 850,
  currentLevelXp: 600,
  nextLevelXp: 1000,
  xpForNextLevel: 150,
  levelPercentage: 62,
  streak: {
    streak: { current: 7, longest: 12 },
    currentMonth: [{ day: '2026-11-22', state: 'today-pending' }],
    today: '2026-11-22',
  },
  achievements: {
    recent: [],
    obtainedCount: 0,
    catalogCount: 12,
    nextAchievement: null,
  },
  weeklyXp: [{ weekStart: '2026-11-16', xp: 150 }],
}

describe('useEngagementPanelSection transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({ accessToken: 'learner-access' })
  })
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('maps the authenticated upstream read into the section state', async () => {
    const requests = installGamificationTransport(body)
    const { result } = renderHook(() => useEngagementPanelSection(), {
      wrapper: createQueryWrapper(),
    })

    await waitFor(() => expect(result.current.state).toBe('success'))
    expect(result.current.monthLabel).toBe('Novembro de 2026')
    expect(result.current.weeklyXp).toEqual([
      { key: '2026-11-16', label: '16 nov', value: 150, valueLabel: '150 XP' },
    ])
    expect(requests).toHaveLength(1)
    expect(requests[0].method).toBe('get')
    expect(requests[0].baseURL).toBe('http://upstream.test')
    expect(requests[0].url).toBe('/gamification/overview')
    expect(requests[0].headers.get('Authorization')).toBe('Bearer learner-access')
    expect(requests[0].headers.get('X-Shifu-Bff-Secret')).toBe('server-owned-secret')
    expect(requests[0].withCredentials).toBe(false)
  })

  it('turns a failed upstream read into the section error state without values', async () => {
    const requests = installGamificationTransport({ message: 'Indisponível.' }, 503)
    const { result } = renderHook(() => useEngagementPanelSection(), {
      wrapper: createQueryWrapper(),
    })

    await waitFor(() => expect(result.current.state).toBe('error'))
    expect(result.current.weeklyXp).toEqual([])
    expect(result.current.monthDays).toEqual([])
    expect(requests).toHaveLength(1)
  })

  it('shares one request between the summary and the section, and one retry recovers both', async () => {
    const requests = installGamificationTransport({ message: 'Indisponível.' }, 503)
    const { result } = renderHook(
      () => ({ summary: useEngagementSummary(), section: useEngagementPanelSection() }),
      { wrapper: createQueryWrapper() },
    )

    await waitFor(() => {
      expect(result.current.summary.state).toBe('error')
      expect(result.current.section.state).toBe('error')
    })
    expect(requests).toHaveLength(1)

    vi.restoreAllMocks()
    const retryRequests = installGamificationTransport(body)
    result.current.section.handleRetry()

    await waitFor(() => {
      expect(result.current.summary.state).toBe('success')
      expect(result.current.section.state).toBe('success')
    })
    expect(result.current.summary.summary?.level).toBe(4)
    expect(retryRequests).toHaveLength(1)
  })
})

describe('getOverview server function', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({ accessToken: 'learner-access' })
  })
  afterEach(() => vi.restoreAllMocks())

  it('returns the overview on success', async () => {
    installGamificationTransport(body)

    expect(await getOverview()).toEqual({ kind: 'success', overview: body })
  })

  it('reports unauthorized when there is no current access', async () => {
    mocks.getCurrentAccess.mockResolvedValue(null)
    const requests = installGamificationTransport(body)

    expect(await getOverview()).toEqual({ kind: 'unauthorized' })
    expect(requests).toHaveLength(0)
  })

  it('maps a rejected AuthError by kind', async () => {
    mocks.getCurrentAccess.mockRejectedValueOnce(
      new AuthError('authentication-rejected', 'Sua sessão expirou.', {
        statusCode: 401,
      }),
    )
    mocks.getCurrentAccess.mockRejectedValueOnce(
      new AuthError('unavailable', 'Indisponível.', { statusCode: 503 }),
    )

    expect(await getOverview()).toEqual({ kind: 'unauthorized', statusCode: 401 })
    expect(await getOverview()).toEqual({ kind: 'unavailable', statusCode: 503 })
  })

  it('maps the upstream status code to unauthorized, forbidden or unavailable', async () => {
    installGamificationTransport({ message: 'Não autorizado.' }, 401)
    expect(await getOverview()).toEqual({ kind: 'unauthorized' })
    vi.restoreAllMocks()

    installGamificationTransport({ message: 'Proibido.' }, 403)
    expect(await getOverview()).toEqual({ kind: 'forbidden' })
    vi.restoreAllMocks()

    installGamificationTransport({ message: 'Indisponível.' }, 503)
    expect(await getOverview()).toEqual({ kind: 'unavailable', statusCode: 503 })
  })

  it('maps an unknown rejection to unavailable', async () => {
    mocks.getCurrentAccess.mockRejectedValue(new Error('boom'))

    expect(await getOverview()).toEqual({ kind: 'unavailable' })
  })
})

describe('useGamificationOverviewQuery queryFn mapping', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getCurrentAccess.mockResolvedValue({ accessToken: 'learner-access' })
  })
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('resolves the overview on success', async () => {
    installGamificationTransport(body)
    const { result } = renderHook(() => useGamificationOverviewQuery(), {
      wrapper: createQueryWrapper(),
    })

    await waitFor(() => expect(result.current.overview).toEqual(body))
    expect(result.current.overviewError).toBeNull()
    expect(result.current.isLoadingOverview).toBe(false)
  })

  it('throws an AuthError when the server function reports unauthorized or forbidden', async () => {
    mocks.getCurrentAccess.mockResolvedValueOnce(null)
    const unauthorized = renderHook(() => useGamificationOverviewQuery(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => expect(unauthorized.result.current.overviewError).not.toBeNull())
    expect(unauthorized.result.current.overviewError).toBeInstanceOf(AuthError)

    installGamificationTransport({ message: 'Proibido.' }, 403)
    const forbidden = renderHook(() => useGamificationOverviewQuery(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => expect(forbidden.result.current.overviewError).not.toBeNull())
    expect(forbidden.result.current.overviewError).toBeInstanceOf(AuthError)
  })

  it('throws a RestError when the server function is unavailable, with and without a status code', async () => {
    mocks.getCurrentAccess.mockRejectedValueOnce(new Error('boom'))
    const withoutStatus = renderHook(() => useGamificationOverviewQuery(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => expect(withoutStatus.result.current.overviewError).not.toBeNull())
    expect(withoutStatus.result.current.overviewError).toBeInstanceOf(RestError)
    expect((withoutStatus.result.current.overviewError as RestError).statusCode).toBe(503)

    installGamificationTransport({ message: 'Bad gateway.' }, 502)
    const withStatus = renderHook(() => useGamificationOverviewQuery(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => expect(withStatus.result.current.overviewError).not.toBeNull())
    expect((withStatus.result.current.overviewError as RestError).statusCode).toBe(502)
  })

  it('refetches on retry', async () => {
    const requests = installGamificationTransport(body)
    const { result } = renderHook(() => useGamificationOverviewQuery(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => expect(result.current.overview).toEqual(body))

    await result.current.refetchOverview()

    expect(requests).toHaveLength(2)
  })
})
