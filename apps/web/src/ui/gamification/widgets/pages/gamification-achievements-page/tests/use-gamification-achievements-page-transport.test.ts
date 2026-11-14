import type { AchievementsOverview } from '@/core/gamification/achievements-overview'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createQueryWrapper,
  installGamificationTransport,
  REQUEST_ID,
  telemetry,
} from '@/ui/gamification/tests/transport-test-support'
import { useGamificationAchievementsPage } from '../use-gamification-achievements-page'

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

describe('useGamificationAchievementsPage transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('maps the authenticated upstream read into the consuming widget state', async () => {
    const body: AchievementsOverview = {
      level: 5,
      totalXp: 1240,
      xpForNextLevel: 260,
      achievements: [
        {
          code: 'first',
          name: 'Primeiro Passo',
          family: 'diagnosis',
          description: 'Concluir um diagnóstico.',
          criterionLabel: '1 diagnóstico concluído',
          xpReward: 25,
          state: 'obtained',
          unlockedAt: '2026-10-25T12:00:00Z',
          progressCurrent: null,
          progressTarget: null,
        },
      ],
    }
    const requests = installGamificationTransport(body)
    const { result } = renderHook(() => useGamificationAchievementsPage(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => {
      expect(result.current.state).toBe('success')
      expect(result.current.familyGroups[0].achievements).toEqual(body.achievements)
      expect(result.current.achievementsProgress).toEqual({
        obtainedCount: 1,
        catalogCount: 1,
      })
    })
    expect(requests).toHaveLength(1)
    expect(requests[0].method).toBe('get')
    expect(requests[0].baseURL).toBe('http://upstream.test')
    expect(requests[0].url).toBe('/gamification/achievements')
    expect(requests[0].headers.get('Authorization')).toBe('Bearer learner-access')
    expect(requests[0].headers.get('X-Shifu-Bff-Secret')).toBe('server-owned-secret')
    expect(requests[0].withCredentials).toBe(false)
    expect(requests[0].headers.get('X-Request-ID')).toBe(REQUEST_ID)
    expect(telemetry.emit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'http.request.completed',
        request_id: REQUEST_ID,
        method: 'GET',
        status_code: 200,
      }),
    )
  })

  it('turns a failed upstream read into the widget error state without success data', async () => {
    const requests = installGamificationTransport({ message: 'Indisponível.' }, 503)
    const { result } = renderHook(() => useGamificationAchievementsPage(), {
      wrapper: createQueryWrapper(),
    })
    await waitFor(() => {
      expect(result.current.state).toBe('error')
      expect(result.current.familyGroups).toEqual([])
    })
    expect(requests).toHaveLength(1)
  })
})
