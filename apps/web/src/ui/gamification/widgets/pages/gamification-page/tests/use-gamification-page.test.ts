import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { Achievement } from '@/core/gamification/achievement'
import type { AchievementsOverview } from '@/core/gamification/achievements-overview'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useAchievementsQuery } from '../use-achievements-query'
import { useGamificationPage } from '../use-gamification-page'

vi.mock('../use-achievements-query', () => ({ useAchievementsQuery: vi.fn() }))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({ useNavigation: vi.fn() }))

const useAchievementsQueryMock = vi.mocked(useAchievementsQuery)
const useNavigationMock = vi.mocked(useNavigation)
const navigateToMock = vi.fn()
const refetchOverviewMock = vi.fn()

const diagnosticObtained: Achievement = {
  code: 'primeiro-passo',
  family: 'diagnosis',
  name: 'Primeiro Passo',
  description: '1 diagnóstico concluído.',
  criterionLabel: '1 diagnóstico concluído',
  xpReward: 25,
  state: 'obtained',
  unlockedAt: '2026-01-15T10:00:00Z',
  progressCurrent: null,
  progressTarget: null,
}

const diagnosticLocked: Achievement = {
  code: 'explorador',
  family: 'diagnosis',
  name: 'Explorador',
  description: '5 diagnósticos concluídos.',
  criterionLabel: '5 diagnósticos concluídos',
  xpReward: 75,
  state: 'locked',
  unlockedAt: null,
  progressCurrent: 1,
  progressTarget: 5,
}

const masteryLocked: Achievement = {
  code: 'primeiro-dominio',
  family: 'mastery',
  name: 'Primeiro Domínio',
  description: '1 Competência dominada.',
  criterionLabel: '1 Competência dominada',
  xpReward: 25,
  state: 'locked',
  unlockedAt: null,
  progressCurrent: 0,
  progressTarget: 1,
}

const levelObtained: Achievement = {
  code: 'ascendente-i',
  family: 'level',
  name: 'Ascendente I',
  description: 'nível 5.',
  criterionLabel: 'nível 5',
  xpReward: 100,
  state: 'obtained',
  unlockedAt: '2026-02-01T00:00:00Z',
  progressCurrent: null,
  progressTarget: null,
}

const retiredHistorical: Achievement = {
  code: 'retired-achievement',
  family: 'diagnosis',
  name: 'Conquista Retirada',
  description: '',
  criterionLabel: '1 diagnóstico concluído',
  xpReward: 25,
  state: 'historical',
  unlockedAt: '2025-10-01T00:00:00Z',
  progressCurrent: null,
  progressTarget: null,
}

const overview: AchievementsOverview = {
  level: 2,
  totalXp: 125,
  xpForNextLevel: 175,
  achievements: [levelObtained, diagnosticObtained, masteryLocked, diagnosticLocked],
}

function mockQuery(overrides: Partial<ReturnType<typeof useAchievementsQuery>> = {}) {
  useAchievementsQueryMock.mockReturnValue({
    overview: null,
    overviewError: null,
    isLoadingOverview: false,
    isFetchingOverview: false,
    refetchOverview: refetchOverviewMock,
    ...overrides,
  })
}

describe('useGamificationPage', () => {
  beforeEach(() => {
    navigateToMock.mockReset()
    refetchOverviewMock.mockReset()
    useAchievementsQueryMock.mockReset()
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToGoalDetail: vi.fn(),
      navigateToActivity: vi.fn(),
      navigateToPlanner: vi.fn(),
    })
    mockQuery()
  })

  it('classifies loading, error and empty states without grouping or summarizing', () => {
    mockQuery({ isLoadingOverview: true })
    const { result, rerender } = renderHook(() => useGamificationPage())
    expect(result.current.state).toBe('loading')
    expect(result.current.familyGroups).toEqual([])
    expect(result.current.profileSummary).toBeNull()

    mockQuery({ overviewError: new RestError('Unavailable.', 503) })
    rerender()
    expect(result.current.state).toBe('error')
    expect(result.current.familyGroups).toEqual([])
    expect(result.current.profileSummary).toBeNull()

    mockQuery({ overview: { ...overview, achievements: [] } })
    rerender()
    expect(result.current.state).toBe('empty')
    expect(result.current.familyGroups).toEqual([])
    expect(result.current.profileSummary).toBeNull()
  })

  it('groups achievements by the canonical family order, dropping empty families', () => {
    mockQuery({ overview })
    const { result } = renderHook(() => useGamificationPage())

    expect(result.current.state).toBe('success')
    expect(result.current.familyGroups.map((group) => group.family)).toEqual([
      'diagnosis',
      'mastery',
      'level',
    ])
    expect(result.current.familyGroups[0]?.achievements).toEqual([
      diagnosticObtained,
      diagnosticLocked,
    ])
    expect(result.current.familyGroups[1]?.achievements).toEqual([masteryLocked])
    expect(result.current.familyGroups[2]?.achievements).toEqual([levelObtained])
  })

  it('keeps a historical achievement out of its resolved family group', () => {
    mockQuery({
      overview: {
        ...overview,
        achievements: [...overview.achievements, retiredHistorical],
      },
    })
    const { result } = renderHook(() => useGamificationPage())

    const diagnosisGroup = result.current.familyGroups.find(
      (group) => group.family === 'diagnosis',
    )
    expect(diagnosisGroup?.achievements).toEqual([diagnosticObtained, diagnosticLocked])
    expect(result.current.historicalAchievements).toEqual([retiredHistorical])
  })

  it('passes the real profile overview (level, totalXp, xpForNextLevel) straight through', () => {
    mockQuery({ overview })
    const { result } = renderHook(() => useGamificationPage())

    expect(result.current.profileSummary).toEqual({
      level: 2,
      totalXp: 125,
      xpForNextLevel: 175,
    })
  })

  it('delegates explicit retry to the underlying query', () => {
    mockQuery({ overview })
    const { result } = renderHook(() => useGamificationPage())
    result.current.handleRetry()
    expect(refetchOverviewMock).toHaveBeenCalledOnce()
  })

  it('reports fetching-without-initial-load as a retry in progress', () => {
    mockQuery({ overview, isFetchingOverview: true })
    const { result } = renderHook(() => useGamificationPage())
    expect(result.current.isRetrying).toBe(true)

    mockQuery({ isLoadingOverview: true, isFetchingOverview: true })
    const { result: initialLoadResult } = renderHook(() => useGamificationPage())
    expect(initialLoadResult.current.isRetrying).toBe(false)
  })

  it('redirects to login when the session is rejected', async () => {
    mockQuery({
      overviewError: new AuthError('authentication-rejected', 'Expired.', {
        statusCode: 401,
      }),
    })
    const { result } = renderHook(() => useGamificationPage())
    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('login'))
    expect(result.current.state).toBe('error')
  })
})
