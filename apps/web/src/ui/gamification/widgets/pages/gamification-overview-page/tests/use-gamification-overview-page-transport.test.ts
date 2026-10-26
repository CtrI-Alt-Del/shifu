import type { GamificationOverview } from '@/core/gamification/overview'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createQueryWrapper,
  installGamificationTransport,
} from '@/ui/gamification/tests/transport-test-support'
import { useGamificationOverviewPage } from '../use-gamification-overview-page'

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
  getBetterAuthProvider: () => ({
    getCurrentAccess: async () => ({ accessToken: 'learner-access' }),
  }),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: () => ({ navigateTo: vi.fn() }),
}))

describe('useGamificationOverviewPage transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('maps the authenticated upstream read into the consuming widget state', async () => {
    const body: GamificationOverview = {
      level: 5,
      totalXp: 1240,
      currentLevelXp: 1000,
      nextLevelXp: 1500,
      xpForNextLevel: 260,
      levelPercentage: 48,
      streak: {
        streak: { current: 0, longest: 0 },
        lastSevenDays: [],
        today: '2026-10-25',
        isTodayPending: true,
      },
      achievements: { recent: [], obtainedCount: 0, catalogCount: 12 },
    }
    const requests = installGamificationTransport(body)
    const { result } = renderHook(() => useGamificationOverviewPage(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => {
      expect(result.current.state).toBe('success')
      expect(result.current.overview).toEqual(body)
    })
    expect(requests).toHaveLength(1)
    expect(requests[0].method).toBe('get')
    expect(requests[0].baseURL).toBe('http://upstream.test')
    expect(requests[0].url).toBe('/gamification/overview')
    expect(requests[0].headers.get('Authorization')).toBe('Bearer learner-access')
    expect(requests[0].headers.get('X-Shifu-Bff-Secret')).toBe('server-owned-secret')
    expect(requests[0].withCredentials).toBe(false)
  })

  it('turns a failed upstream read into the widget error state without success data', async () => {
    const requests = installGamificationTransport({ message: 'Indisponível.' }, 503)
    const { result } = renderHook(() => useGamificationOverviewPage(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => {
      expect(result.current.state).toBe('error')
      expect(result.current.overview).toBeNull()
    })
    expect(requests).toHaveLength(1)
  })
})
