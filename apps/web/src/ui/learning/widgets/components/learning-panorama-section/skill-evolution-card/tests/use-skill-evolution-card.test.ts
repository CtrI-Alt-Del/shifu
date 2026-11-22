import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { EvolutionOption } from '@/core/learning/learning-panorama'
import type { SkillEvolution } from '@/core/learning/skill-evolution'

import { useSkillEvolutionCard } from '../use-skill-evolution-card'
import { useSkillEvolutionQuery } from '../use-skill-evolution-query'

vi.mock('../use-skill-evolution-query', () => ({ useSkillEvolutionQuery: vi.fn() }))

const useSkillEvolutionQueryMock = vi.mocked(useSkillEvolutionQuery)
const refetchSkillEvolutionMock = vi.fn()

const options: EvolutionOption[] = [
  {
    skillExperienceId: 'exp-python',
    goalTitle: 'Carreira em dados',
    skillName: 'Python para análise de dados',
    status: 'learning',
  },
  {
    skillExperienceId: 'exp-logic-a',
    goalTitle: 'Carreira em dados',
    skillName: 'Lógica de programação',
    status: 'completed',
  },
  {
    skillExperienceId: 'exp-logic-b',
    goalTitle: 'Aprender a programar',
    skillName: 'Lógica de programação',
    status: 'learning',
  },
]

const evolution: SkillEvolution = {
  skillExperienceId: 'exp-python',
  points: [
    {
      occurredAt: '2026-09-28T15:00:00Z',
      result: 42.4,
      isPartial: true,
      isBaseline: true,
    },
    {
      occurredAt: '2026-10-05T15:00:00Z',
      result: 55,
      isPartial: true,
      isBaseline: false,
    },
    {
      occurredAt: '2026-10-12T15:00:00Z',
      result: 68.6,
      isPartial: false,
      isBaseline: false,
    },
  ],
}

function mockQuery(overrides: Partial<ReturnType<typeof useSkillEvolutionQuery>> = {}) {
  useSkillEvolutionQueryMock.mockReturnValue({
    skillEvolution: evolution,
    skillEvolutionError: null,
    isLoadingSkillEvolution: false,
    isFetchingSkillEvolution: false,
    refetchSkillEvolution: refetchSkillEvolutionMock,
    ...overrides,
  } as ReturnType<typeof useSkillEvolutionQuery>)
}

function renderCardHook(
  props: { options: EvolutionOption[]; defaultSkillExperienceId: string | null } = {
    options,
    defaultSkillExperienceId: 'exp-python',
  },
) {
  return renderHook((hookProps) => useSkillEvolutionCard(hookProps), {
    initialProps: props,
  })
}

describe('useSkillEvolutionCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockQuery()
  })

  it('starts on the default experience and queries only that selection', () => {
    const { result } = renderCardHook()

    expect(result.current.selectedSkillExperienceId).toBe('exp-python')
    expect(useSkillEvolutionQueryMock).toHaveBeenLastCalledWith('exp-python')
  })

  it('labels options by Habilidade and adds the Objetivo only when the name repeats', () => {
    const { result } = renderCardHook()

    expect(result.current.selectOptions).toEqual([
      { value: 'exp-python', label: 'Python para análise de dados' },
      { value: 'exp-logic-a', label: 'Lógica de programação · Carreira em dados' },
      { value: 'exp-logic-b', label: 'Lógica de programação · Aprender a programar' },
    ])
  })

  it('maps the points to chart data with partial notes and the baseline wording', () => {
    const { result } = renderCardHook()

    expect(result.current.evolutionData).toEqual([
      {
        key: '2026-09-28T15:00:00Z-0',
        label: '28 set',
        value: 42.4,
        valueLabel: '42% (ponto de partida)',
        note: 'Parcial',
      },
      {
        key: '2026-10-05T15:00:00Z-1',
        label: '5 out',
        value: 55,
        valueLabel: '55%',
        note: 'Parcial',
      },
      {
        key: '2026-10-12T15:00:00Z-2',
        label: '12 out',
        value: 68.6,
        valueLabel: '69%',
        note: undefined,
      },
    ])
    expect(result.current.baselineLabel).toBe('Ponto de partida · 42%')
    expect(result.current.description).toBe(
      'Resultado da Habilidade após cada avaliação, desde o diagnóstico · pontos vazados são estimativas parciais',
    )
    expect(result.current.state).toBe('success')
    expect(result.current.isRetrying).toBe(false)
  })

  it('drops the starting point wording when the series has no baseline', () => {
    mockQuery({
      skillEvolution: {
        skillExperienceId: 'exp-python',
        points: [
          {
            occurredAt: '2026-10-05T15:00:00Z',
            result: 55,
            isPartial: false,
            isBaseline: false,
          },
        ],
      },
    })

    const { result } = renderCardHook()

    expect(result.current.baselineLabel).toBeUndefined()
    expect(result.current.description).toBe(
      'Resultado da Habilidade após cada avaliação · pontos vazados são estimativas parciais',
    )
  })

  it('reloads the series for the chosen experience only', () => {
    const { result } = renderCardHook()

    act(() => result.current.handleSelectSkillExperience('exp-logic-b'))

    expect(result.current.selectedSkillExperienceId).toBe('exp-logic-b')
    expect(useSkillEvolutionQueryMock).toHaveBeenLastCalledWith('exp-logic-b')
  })

  it('ignores a cleared selection', () => {
    const { result } = renderCardHook()

    act(() => result.current.handleSelectSkillExperience(null))

    expect(result.current.selectedSkillExperienceId).toBe('exp-python')
  })

  it('falls back to the default when the chosen experience leaves the options', () => {
    const { result, rerender } = renderCardHook()
    act(() => result.current.handleSelectSkillExperience('exp-logic-b'))

    rerender({ options: options.slice(0, 2), defaultSkillExperienceId: 'exp-python' })

    expect(result.current.selectedSkillExperienceId).toBe('exp-python')
    expect(useSkillEvolutionQueryMock).toHaveBeenLastCalledWith('exp-python')
  })

  it('is empty and queries nothing without a default selection', () => {
    mockQuery({ skillEvolution: null, isLoadingSkillEvolution: false })

    const { result } = renderCardHook({ options, defaultSkillExperienceId: null })

    expect(result.current.selectedSkillExperienceId).toBeNull()
    expect(result.current.state).toBe('empty')
    expect(useSkillEvolutionQueryMock).toHaveBeenLastCalledWith(null)
  })

  it('derives the loading state while the selected series loads', () => {
    mockQuery({
      skillEvolution: null,
      isLoadingSkillEvolution: true,
      isFetchingSkillEvolution: true,
    })

    const { result } = renderCardHook()

    expect(result.current.state).toBe('loading')
    expect(result.current.isRetrying).toBe(false)
    expect(result.current.evolutionData).toEqual([])
  })

  it('derives its own error state and reports a retry in flight', () => {
    mockQuery({
      skillEvolution: null,
      skillEvolutionError: new Error('down'),
      isFetchingSkillEvolution: true,
    })

    const { result } = renderCardHook()

    expect(result.current.state).toBe('error')
    expect(result.current.isRetrying).toBe(true)
  })

  it('derives the error state when the read finished without a series', () => {
    mockQuery({ skillEvolution: null })

    const { result } = renderCardHook()

    expect(result.current.state).toBe('error')
  })

  it('derives the empty state for a series without points', () => {
    mockQuery({ skillEvolution: { skillExperienceId: 'exp-python', points: [] } })

    const { result } = renderCardHook()

    expect(result.current.state).toBe('empty')
    expect(result.current.evolutionData).toEqual([])
    expect(result.current.baselineLabel).toBeUndefined()
  })

  it('derives the empty state when the series holds only the diagnostic base point', () => {
    mockQuery({
      skillEvolution: { ...evolution, points: [evolution.points[0]] },
    } as Partial<ReturnType<typeof useSkillEvolutionQuery>>)
    const { result } = renderCardHook()

    expect(result.current.state).toBe('empty')
  })

  it('derives the success state from the base point plus the first evaluation', () => {
    mockQuery({
      skillEvolution: { ...evolution, points: evolution.points.slice(0, 2) },
    } as Partial<ReturnType<typeof useSkillEvolutionQuery>>)
    const { result } = renderCardHook()

    expect(result.current.state).toBe('success')
  })

  it('refetches only the selected series when the retry handler runs', () => {
    const { result } = renderCardHook()

    act(() => result.current.handleRetry())

    expect(refetchSkillEvolutionMock).toHaveBeenCalledTimes(1)
  })
})
