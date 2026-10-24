import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { GamificationOverview } from '@/core/gamification/overview'

import { useOverviewQuery } from '../use-overview-query'
import { useGamificationOverviewPage } from '../use-gamification-overview-page'

vi.mock('../use-overview-query', () => ({ useOverviewQuery: vi.fn() }))

const useOverviewQueryMock = vi.mocked(useOverviewQuery)

const overview: GamificationOverview = {
  level: 5,
  totalXp: 1240,
  currentLevelXp: 1000,
  nextLevelXp: 1500,
  xpForNextLevel: 260,
  levelPercentage: 48,
  streak: {
    streak: { current: 3, longest: 9 },
    lastSevenDays: [
      { day: '2026-09-09', state: 'neutral' },
      { day: '2026-09-10', state: 'missed' },
      { day: '2026-09-11', state: 'practiced' },
      { day: '2026-09-12', state: 'current-streak' },
      { day: '2026-09-13', state: 'current-streak' },
      { day: '2026-09-14', state: 'current-streak' },
      { day: '2026-09-15', state: 'today-pending' },
    ],
    today: '2026-09-15',
    isTodayPending: true,
  },
  achievements: {
    recent: [
      {
        achievementId: 'consistencia-ii',
        name: 'Consistência II',
        criterionLabel: '7 dias consecutivos',
        xpReward: 50,
        achievedAt: '2026-09-13T12:00:00Z',
      },
    ],
    obtainedCount: 4,
    catalogCount: 12,
  },
}

const emptyOverview: GamificationOverview = {
  ...overview,
  level: 1,
  totalXp: 0,
  currentLevelXp: 0,
  nextLevelXp: 100,
  xpForNextLevel: 100,
  levelPercentage: 0,
  streak: { ...overview.streak, streak: { current: 0, longest: 0 } },
  achievements: { recent: [], obtainedCount: 0, catalogCount: 12 },
}

function mockQuery(overrides: Partial<ReturnType<typeof useOverviewQuery>> = {}) {
  const refetchOverview = vi.fn()
  useOverviewQueryMock.mockReturnValue({
    overview,
    overviewError: null,
    isLoadingOverview: false,
    isFetchingOverview: false,
    refetchOverview,
    ...overrides,
  } as unknown as ReturnType<typeof useOverviewQuery>)
  return refetchOverview
}

describe('useGamificationOverviewPage', () => {
  beforeEach(() => useOverviewQueryMock.mockReset())

  it('reports the loading state while the query is pending', () => {
    mockQuery({ isLoadingOverview: true, overview: null })
    const { result } = renderHook(() => useGamificationOverviewPage())

    expect(result.current.state).toBe('loading')
    expect(result.current.overview).toBeNull()
  })

  it('reports the error state when the query rejects or returns nothing', () => {
    mockQuery({ overviewError: new RestError('Unavailable.', 503) })
    const { result, rerender } = renderHook(() => useGamificationOverviewPage())
    expect(result.current.state).toBe('error')
    expect(result.current.overview).toBeNull()

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
  })

  it('reports the initial state for an account with no reward at all', () => {
    mockQuery({ overview: emptyOverview })
    const { result } = renderHook(() => useGamificationOverviewPage())

    expect(result.current.state).toBe('empty')
    expect(result.current.overview).toBeNull()
  })

  it('keeps a rewarded account out of the initial state', () => {
    mockQuery({
      overview: {
        ...emptyOverview,
        streak: { ...emptyOverview.streak, streak: { current: 0, longest: 2 } },
      },
    })
    const { result } = renderHook(() => useGamificationOverviewPage())

    expect(result.current.state).toBe('success')
  })

  it('exposes the overview values on success', () => {
    mockQuery()
    const { result } = renderHook(() => useGamificationOverviewPage())

    expect(result.current.state).toBe('success')
    expect(result.current.overview).toEqual(overview)
  })

  it('reports fetching-without-initial-load as a retry in progress', () => {
    mockQuery({ isFetchingOverview: true })
    const { result } = renderHook(() => useGamificationOverviewPage())
    expect(result.current.isRetrying).toBe(true)

    mockQuery({ isLoadingOverview: true, isFetchingOverview: true, overview: null })
    const { result: initialLoad } = renderHook(() => useGamificationOverviewPage())
    expect(initialLoad.current.isRetrying).toBe(false)
  })

  it('delegates explicit retry to the underlying query', () => {
    const refetchOverview = mockQuery({ overviewError: new RestError('Down.', 503) })
    const { result } = renderHook(() => useGamificationOverviewPage())

    result.current.handleRetry()

    expect(refetchOverview).toHaveBeenCalledOnce()
  })
})
