import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { GamificationOverview } from '@/core/gamification/overview'
import { useGamificationOverviewQuery } from '@/ui/gamification/hooks/use-gamification-overview-query'

import { useEngagementSummary } from '../use-engagement-summary'

vi.mock('@/ui/gamification/hooks/use-gamification-overview-query', () => ({
  useGamificationOverviewQuery: vi.fn(),
}))

const useGamificationOverviewQueryMock = vi.mocked(useGamificationOverviewQuery)

const overview: GamificationOverview = {
  level: 4,
  totalXp: 1240,
  currentLevelXp: 600,
  nextLevelXp: 1000,
  xpForNextLevel: 150,
  levelPercentage: 62,
  streak: {
    streak: { current: 7, longest: 12 },
    currentMonth: [{ day: '2026-11-01', state: 'missed' }],
    today: '2026-11-22',
  },
  achievements: {
    recent: [],
    obtainedCount: 0,
    catalogCount: 12,
    nextAchievement: null,
  },
  weeklyXp: [],
}

function mockQuery(
  overrides: Partial<ReturnType<typeof useGamificationOverviewQuery>> = {},
) {
  const refetchOverview = vi.fn()
  useGamificationOverviewQueryMock.mockReturnValue({
    overview,
    overviewError: null,
    isLoadingOverview: false,
    isFetchingOverview: false,
    refetchOverview,
    ...overrides,
  } as unknown as ReturnType<typeof useGamificationOverviewQuery>)
  return refetchOverview
}

describe('useEngagementSummary', () => {
  beforeEach(() => useGamificationOverviewQueryMock.mockReset())

  it('reports the loading state without values while the overview is pending', () => {
    mockQuery({ isLoadingOverview: true, isFetchingOverview: true, overview: null })
    const { result } = renderHook(() => useEngagementSummary())

    expect(result.current.state).toBe('loading')
    expect(result.current.summary).toBeNull()
    expect(result.current.isRetrying).toBe(false)
  })

  it('reports the error state when the query rejects or returns nothing', () => {
    mockQuery({ overviewError: new RestError('Unavailable.', 503) })
    const { result, rerender } = renderHook(() => useEngagementSummary())
    expect(result.current.state).toBe('error')
    expect(result.current.summary).toBeNull()

    mockQuery({
      overviewError: new AuthError('authentication-rejected', 'Expired.', {
        statusCode: 401,
      }),
    })
    rerender()
    expect(result.current.state).toBe('error')

    mockQuery({ overview: null })
    rerender()
    expect(result.current.state).toBe('error')
    expect(result.current.summary).toBeNull()
  })

  it('exposes level, XP and streak values from the overview on success', () => {
    mockQuery()
    const { result } = renderHook(() => useEngagementSummary())

    expect(result.current.state).toBe('success')
    expect(result.current.summary).toEqual({
      level: 4,
      totalXp: 1240,
      xpForNextLevel: 150,
      levelPercentage: 62,
      currentStreak: 7,
      longestStreak: 12,
    })
  })

  it('keeps a new account with no XP and no streak in the success state', () => {
    mockQuery({
      overview: {
        ...overview,
        level: 1,
        totalXp: 0,
        xpForNextLevel: 100,
        levelPercentage: 0,
        streak: { ...overview.streak, streak: { current: 0, longest: 0 } },
      },
    })
    const { result } = renderHook(() => useEngagementSummary())

    expect(result.current.state).toBe('success')
    expect(result.current.summary?.totalXp).toBe(0)
  })

  it('formats XP amounts with the pt-BR thousands separator', () => {
    mockQuery()
    const { result } = renderHook(() => useEngagementSummary())

    expect(result.current.formatXp(1240)).toBe('1.240')
  })

  it('reports a refetch after the first load as a retry in progress', () => {
    mockQuery({ isFetchingOverview: true })
    const { result } = renderHook(() => useEngagementSummary())

    expect(result.current.isRetrying).toBe(true)
  })

  it('delegates the explicit retry to the underlying query', () => {
    const refetchOverview = mockQuery({ overviewError: new RestError('Down.', 503) })
    const { result } = renderHook(() => useEngagementSummary())

    result.current.handleRetry()

    expect(refetchOverview).toHaveBeenCalledOnce()
  })
})
