import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type {
  AchievementCriterionKind,
  GamificationOverview,
} from '@/core/gamification/overview'
import { useGamificationOverviewQuery } from '@/ui/gamification/hooks/use-gamification-overview-query'

import { useEngagementPanelSection } from '../use-engagement-panel-section'

vi.mock('@/ui/gamification/hooks/use-gamification-overview-query', () => ({
  useGamificationOverviewQuery: vi.fn(),
}))

const useGamificationOverviewQueryMock = vi.mocked(useGamificationOverviewQuery)

const overview: GamificationOverview = {
  level: 4,
  totalXp: 850,
  currentLevelXp: 600,
  nextLevelXp: 1000,
  xpForNextLevel: 150,
  levelPercentage: 62,
  streak: {
    streak: { current: 7, longest: 12 },
    currentMonth: [
      { day: '2026-11-01', state: 'missed' },
      { day: '2026-11-21', state: 'current-streak' },
      { day: '2026-11-22', state: 'today-pending' },
    ],
    today: '2026-11-22',
  },
  achievements: {
    recent: [
      {
        achievementId: 'consistencia-ii',
        name: 'Consistência II',
        criterionLabel: '7 dias consecutivos',
        xpReward: 50,
        achievedAt: '2026-11-21T12:00:00Z',
      },
      {
        achievementId: 'conquista-aposentada',
        name: 'Conquista antiga',
        criterionLabel: 'Critério antigo',
        xpReward: 100,
        achievedAt: '2026-09-08T12:00:00Z',
      },
    ],
    obtainedCount: 5,
    catalogCount: 12,
    nextAchievement: {
      achievementId: 'consistencia-iii',
      name: 'Consistência III',
      criterionLabel: '30 dias consecutivos',
      criterionKind: 'longest_streak',
      xpReward: 150,
      progressCurrent: 12,
      progressTarget: 30,
    },
  },
  weeklyXp: [
    { weekStart: '2026-08-31', xp: 20 },
    { weekStart: '2026-09-07', xp: 0 },
    { weekStart: '2026-11-16', xp: 150 },
  ],
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

describe('useEngagementPanelSection', () => {
  beforeEach(() => useGamificationOverviewQueryMock.mockReset())

  it('reports the loading state with no values while the overview is pending', () => {
    mockQuery({ isLoadingOverview: true, isFetchingOverview: true, overview: null })
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.state).toBe('loading')
    expect(result.current.monthLabel).toBe('')
    expect(result.current.monthDays).toEqual([])
    expect(result.current.recentAchievements).toEqual([])
    expect(result.current.nextAchievement).toBeNull()
    expect(result.current.weeklyXp).toEqual([])
    expect(result.current.isRetrying).toBe(false)
  })

  it('reports the error state without inventing values', () => {
    mockQuery({ overviewError: new RestError('Unavailable.', 503) })
    const { result, rerender } = renderHook(() => useEngagementPanelSection())
    expect(result.current.state).toBe('error')
    expect(result.current.monthDays).toEqual([])
    expect(result.current.weeklyXp).toEqual([])

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
    expect(result.current.nextAchievement).toBeNull()
  })

  it('names the current local month and exposes its days', () => {
    mockQuery()
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.state).toBe('success')
    expect(result.current.monthLabel).toBe('Novembro de 2026')
    expect(result.current.monthDays).toEqual(overview.streak.currentMonth)
  })

  it('maps each recent achievement to its text, XP label, date and icon', () => {
    mockQuery()
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.recentAchievements).toEqual([
      {
        id: 'consistencia-ii',
        name: 'Consistência II',
        criterionLabel: '7 dias consecutivos',
        xpLabel: '+50 XP',
        achievedOn: '21 nov 2026',
        icon: 'flame',
      },
      {
        id: 'conquista-aposentada',
        name: 'Conquista antiga',
        criterionLabel: 'Critério antigo',
        xpLabel: '+100 XP',
        achievedOn: '8 set 2026',
        icon: 'trophy',
      },
    ])
  })

  it('maps the next achievement with its progress label, percentage and hint', () => {
    mockQuery()
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.nextAchievement).toEqual({
      name: 'Consistência III',
      criterionLabel: '30 dias consecutivos',
      progressLabel: '12 de 30',
      progressPercentage: 40,
      hint: 'Baseada no seu recorde de sequência.',
    })
  })

  it.each<[AchievementCriterionKind, string]>([
    ['diagnostics_completed', 'Baseada nos seus diagnósticos concluídos.'],
    ['competencies_mastered', 'Baseada nas suas Competências dominadas.'],
    ['skills_completed', 'Baseada nas suas Habilidades concluídas.'],
    ['longest_streak', 'Baseada no seu recorde de sequência.'],
    ['level', 'Baseada no seu nível.'],
  ])('explains where the %s progress comes from', (criterionKind, hint) => {
    const base = overview.achievements.nextAchievement
    if (!base) throw new Error('fixture without next achievement')
    mockQuery({
      overview: {
        ...overview,
        achievements: {
          ...overview.achievements,
          nextAchievement: { ...base, criterionKind },
        },
      },
    })
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.nextAchievement?.hint).toBe(hint)
  })

  it('omits the next achievement when none is returned', () => {
    mockQuery({
      overview: {
        ...overview,
        achievements: { ...overview.achievements, nextAchievement: null },
      },
    })
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.nextAchievement).toBeNull()
  })

  it('reports zero progress for a next achievement with an empty target', () => {
    const base = overview.achievements.nextAchievement
    if (!base) throw new Error('fixture without next achievement')
    mockQuery({
      overview: {
        ...overview,
        achievements: {
          ...overview.achievements,
          nextAchievement: { ...base, progressCurrent: 0, progressTarget: 0 },
        },
      },
    })
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.nextAchievement?.progressPercentage).toBe(0)
  })

  it('maps each week of XP to a chart datum labelled by its Monday', () => {
    mockQuery()
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.weeklyXp).toEqual([
      { key: '2026-08-31', label: '31 ago', value: 20, valueLabel: '20 XP' },
      { key: '2026-09-07', label: '7 set', value: 0, valueLabel: '0 XP' },
      { key: '2026-11-16', label: '16 nov', value: 150, valueLabel: '150 XP' },
    ])
  })

  it('reports a refetch after the first load as a retry in progress', () => {
    mockQuery({ isFetchingOverview: true })
    const { result } = renderHook(() => useEngagementPanelSection())

    expect(result.current.isRetrying).toBe(true)
  })

  it('delegates the explicit retry to the underlying query', () => {
    const refetchOverview = mockQuery({ overviewError: new RestError('Down.', 503) })
    const { result } = renderHook(() => useEngagementPanelSection())

    result.current.handleRetry()

    expect(refetchOverview).toHaveBeenCalledOnce()
  })
})
