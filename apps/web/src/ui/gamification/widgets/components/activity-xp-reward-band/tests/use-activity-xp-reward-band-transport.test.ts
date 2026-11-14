import type { ActivityXpReward } from '@/core/gamification/activity-xp-reward'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createQueryWrapper,
  installGamificationTransport,
} from '@/ui/gamification/tests/transport-test-support'
import { useActivityXpRewardBand } from '../use-activity-xp-reward-band'

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

describe('useActivityXpRewardBand transport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('maps the authenticated upstream read into the consuming widget state', async () => {
    const body: ActivityXpReward = {
      activityId: 'activity-1',
      attemptId: 'attempt-1',
      state: 'granted',
      additionalXp: 6,
      grantedXp: 18,
      maximumXp: 20,
    }
    const requests = installGamificationTransport(body)
    const { result } = renderHook(
      () => useActivityXpRewardBand('activity-1', 'attempt-1'),
      { wrapper: createQueryWrapper() },
    )
    await waitFor(() => {
      expect(result.current).toEqual({
        status: 'granted',
        additionalXp: 6,
        grantedXp: 18,
        maximumXp: 20,
      })
    })
    expect(requests).toHaveLength(1)
    expect(requests[0].method).toBe('get')
    expect(requests[0].baseURL).toBe('http://upstream.test')
    expect(requests[0].url).toBe(
      '/gamification/activities/activity-1/attempts/attempt-1/xp-reward',
    )
    expect(requests[0].headers.get('Authorization')).toBe('Bearer learner-access')
    expect(requests[0].headers.get('X-Shifu-Bff-Secret')).toBe('server-owned-secret')
    expect(requests[0].withCredentials).toBe(false)
  })

  it('turns a failed upstream read into the widget error state without success data', async () => {
    const requests = installGamificationTransport({ message: 'Indisponível.' }, 503)
    const { result } = renderHook(
      () => useActivityXpRewardBand('activity-1', 'attempt-1'),
      { wrapper: createQueryWrapper() },
    )
    await waitFor(() => {
      expect(result.current).toEqual({ status: 'unavailable' })
    })
    expect(requests).toHaveLength(1)
  })
})
