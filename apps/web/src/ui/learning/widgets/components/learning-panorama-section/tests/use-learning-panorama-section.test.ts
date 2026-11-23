import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { LearningPanorama } from '@/core/learning/learning-panorama'
import { useLearningPanoramaQuery } from '@/ui/learning/hooks/use-learning-panorama-query'

import { useLearningPanoramaSection } from '../use-learning-panorama-section'

vi.mock('@/ui/learning/hooks/use-learning-panorama-query', () => ({
  useLearningPanoramaQuery: vi.fn(),
}))

const useLearningPanoramaQueryMock = vi.mocked(useLearningPanoramaQuery)
const refetchPanoramaMock = vi.fn()

const panorama: LearningPanorama = {
  hasGoals: true,
  completedSkillCount: 3,
  masteredCompetencyCount: 14,
  stageDistribution: {
    notStarted: 2,
    diagnosing: 1,
    learning: 3,
    completed: 3,
    goalCount: 3,
  },
  resumeItems: [],
  weeklyEvaluatedActivities: [
    { weekStart: '2026-09-28', count: 3 },
    { weekStart: '2026-10-05', count: 0 },
    { weekStart: '2026-10-12', count: 1 },
  ],
  evolutionOptions: [],
  defaultEvolutionSkillExperienceId: null,
  completedSkills: [],
  recentMasteries: [],
}

function mockQuery(overrides: Partial<ReturnType<typeof useLearningPanoramaQuery>> = {}) {
  useLearningPanoramaQueryMock.mockReturnValue({
    panorama,
    panoramaError: null,
    isLoadingPanorama: false,
    isFetchingPanorama: false,
    refetchPanorama: refetchPanoramaMock,
    ...overrides,
  } as ReturnType<typeof useLearningPanoramaQuery>)
}

describe('useLearningPanoramaSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockQuery()
  })

  it('exposes the panorama only in the success state', () => {
    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.state).toBe('success')
    expect(result.current.panorama).toBe(panorama)
    expect(result.current.isRetrying).toBe(false)
  })

  it('derives the loading state and hides the panorama', () => {
    mockQuery({ panorama: null, isLoadingPanorama: true, isFetchingPanorama: true })

    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.state).toBe('loading')
    expect(result.current.panorama).toBeNull()
    expect(result.current.isRetrying).toBe(false)
  })

  it('derives the error state when the read fails and never exposes stale values', () => {
    mockQuery({ panoramaError: new Error('down') })

    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.state).toBe('error')
    expect(result.current.panorama).toBeNull()
    expect(result.current.weeklyData).toEqual([])
    expect(result.current.hasWeeklyData).toBe(false)
  })

  it('derives the error state when the read finished without a panorama', () => {
    mockQuery({ panorama: null })

    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.state).toBe('error')
  })

  it('derives the empty state for an account without Objetivos', () => {
    mockQuery({ panorama: { ...panorama, hasGoals: false } })

    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.state).toBe('empty')
    expect(result.current.panorama).toBeNull()
  })

  it('reports a retry while a refetch runs after the first read', () => {
    mockQuery({ panoramaError: new Error('down'), isFetchingPanorama: true })

    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.isRetrying).toBe(true)
  })

  it('maps the eight local weeks to chart data with the week start label and count', () => {
    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.weeklyData).toEqual([
      { key: '2026-09-28', label: '28 set', value: 3, valueLabel: '3 atividades' },
      { key: '2026-10-05', label: '5 out', value: 0, valueLabel: '0 atividades' },
      { key: '2026-10-12', label: '12 out', value: 1, valueLabel: '1 atividade' },
    ])
    expect(result.current.hasWeeklyData).toBe(true)
  })

  it('reports no weekly data when every week counts zero', () => {
    mockQuery({
      panorama: {
        ...panorama,
        weeklyEvaluatedActivities: [{ weekStart: '2026-09-28', count: 0 }],
      },
    })

    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.hasWeeklyData).toBe(false)
  })

  it('lists the four stages with their counts and the Habilidade and Objetivo summary', () => {
    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.stageItems).toEqual([
      { key: 'not-started', label: 'Não iniciadas', count: 2 },
      { key: 'diagnosing', label: 'Em diagnóstico', count: 1 },
      { key: 'learning', label: 'Em aprendizado', count: 3 },
      { key: 'completed', label: 'Concluídas', count: 3 },
    ])
    expect(result.current.stageSummary).toBe('9 Habilidades em 3 Objetivos')
  })

  it('uses the singular in the stage summary for one Habilidade in one Objetivo', () => {
    mockQuery({
      panorama: {
        ...panorama,
        stageDistribution: {
          notStarted: 0,
          diagnosing: 1,
          learning: 0,
          completed: 0,
          goalCount: 1,
        },
      },
    })

    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.stageSummary).toBe('1 Habilidade em 1 Objetivo')
  })

  it('explains an Objetivo without experiences instead of reporting zero Habilidades', () => {
    mockQuery({
      panorama: {
        ...panorama,
        stageDistribution: {
          notStarted: 0,
          diagnosing: 0,
          learning: 0,
          completed: 0,
          goalCount: 0,
        },
      },
    })

    const { result } = renderHook(() => useLearningPanoramaSection())

    expect(result.current.stageSummary).toBe(
      'Nenhuma Habilidade nos seus Objetivos ainda.',
    )
  })

  it('refetches the panorama when the retry handler runs', () => {
    const { result } = renderHook(() => useLearningPanoramaSection())

    act(() => result.current.handleRetry())

    expect(refetchPanoramaMock).toHaveBeenCalledTimes(1)
  })
})
