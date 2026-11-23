import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { LearningPanorama } from '@/core/learning/learning-panorama'
import { useLearningPanoramaQuery } from '@/ui/learning/hooks/use-learning-panorama-query'

import { useLearningPanoramaSummary } from '../use-learning-panorama-summary'

vi.mock('@/ui/learning/hooks/use-learning-panorama-query', () => ({
  useLearningPanoramaQuery: vi.fn(),
}))

const useLearningPanoramaQueryMock = vi.mocked(useLearningPanoramaQuery)
const refetchPanoramaMock = vi.fn()

const panorama: LearningPanorama = {
  hasGoals: true,
  completedSkillCount: 3,
  masteredCompetencyCount: 1400,
  stageDistribution: {
    notStarted: 2,
    diagnosing: 1,
    learning: 3,
    completed: 3,
    goalCount: 3,
  },
  resumeItems: [],
  weeklyEvaluatedActivities: [],
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

describe('useLearningPanoramaSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockQuery()
  })

  it('derives the success state with both card values', () => {
    const { result } = renderHook(() => useLearningPanoramaSummary())

    expect(result.current.state).toBe('success')
    expect(result.current.cards).toEqual([
      { key: 'completed-skills', caption: 'Habilidades concluídas', value: 3 },
      { key: 'mastered-competencies', caption: 'Competências dominadas', value: 1400 },
    ])
    expect(result.current.isRetrying).toBe(false)
  })

  it('derives the loading state while the first read is pending', () => {
    mockQuery({ panorama: null, isLoadingPanorama: true, isFetchingPanorama: true })

    const { result } = renderHook(() => useLearningPanoramaSummary())

    expect(result.current.state).toBe('loading')
    expect(result.current.isRetrying).toBe(false)
  })

  it('derives the error state with zero values and never invents counts', () => {
    mockQuery({ panorama: null, panoramaError: new Error('down') })

    const { result } = renderHook(() => useLearningPanoramaSummary())

    expect(result.current.state).toBe('error')
    expect(result.current.cards.map((card) => card.value)).toEqual([0, 0])
  })

  it('derives the error state when the read finished without a panorama', () => {
    mockQuery({ panorama: null })

    const { result } = renderHook(() => useLearningPanoramaSummary())

    expect(result.current.state).toBe('error')
  })

  it('derives the empty state for an account without Objetivos', () => {
    mockQuery({
      panorama: {
        ...panorama,
        hasGoals: false,
        completedSkillCount: 0,
        masteredCompetencyCount: 0,
      },
    })

    const { result } = renderHook(() => useLearningPanoramaSummary())

    expect(result.current.state).toBe('empty')
    expect(result.current.cards.map((card) => card.value)).toEqual([0, 0])
  })

  it('reports a retry while a background refetch runs after the first read', () => {
    mockQuery({ panoramaError: new Error('down'), isFetchingPanorama: true })

    const { result } = renderHook(() => useLearningPanoramaSummary())

    expect(result.current.isRetrying).toBe(true)
  })

  it('formats counts with the pt-BR thousands separator', () => {
    const { result } = renderHook(() => useLearningPanoramaSummary())

    expect(result.current.formatCount(1400)).toBe('1.400')
    expect(result.current.formatCount(14)).toBe('14')
  })

  it('refetches the panorama when the retry handler runs', () => {
    const { result } = renderHook(() => useLearningPanoramaSummary())

    act(() => result.current.handleRetry())

    expect(refetchPanoramaMock).toHaveBeenCalledTimes(1)
  })
})
