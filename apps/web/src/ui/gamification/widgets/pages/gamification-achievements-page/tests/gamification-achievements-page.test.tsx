import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Achievement } from '@/core/gamification/achievement'

import { GamificationAchievementsPage } from '..'
import {
  type AchievementFamilyGroup,
  type GamificationAchievementsPageController,
  useGamificationAchievementsPage,
} from '../use-gamification-achievements-page'

// Entrance motion and counters settle at once, so assertions see the final
// state; the shared components own their own animated cases.
vi.mock('motion/react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('motion/react')>()),
  useReducedMotion: vi.fn(() => true),
}))
vi.mock('../use-gamification-achievements-page', () => ({
  useGamificationAchievementsPage: vi.fn(),
}))

const useGamificationAchievementsPageMock = vi.mocked(useGamificationAchievementsPage)

const obtainedAchievement: Achievement = {
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

const lockedAchievement: Achievement = {
  code: 'explorador',
  family: 'diagnosis',
  name: 'Explorador',
  description: '5 diagnósticos concluídos.',
  criterionLabel: '5 diagnósticos concluídos',
  xpReward: 75,
  state: 'locked',
  unlockedAt: null,
  progressCurrent: 2,
  progressTarget: 5,
}

const historicalAchievement: Achievement = {
  code: 'retired-achievement',
  family: 'diagnosis',
  name: 'RETIRED_CODE',
  description: '',
  criterionLabel: '1 diagnóstico concluído',
  xpReward: 25,
  state: 'historical',
  unlockedAt: '2025-11-01T10:00:00Z',
  progressCurrent: null,
  progressTarget: null,
}

const familyGroups: AchievementFamilyGroup[] = [
  {
    family: 'diagnosis',
    achievements: [obtainedAchievement, lockedAchievement],
    obtainedCount: 1,
  },
]

function makeController(
  overrides: Partial<GamificationAchievementsPageController> = {},
): GamificationAchievementsPageController {
  return {
    familyGroups: [],
    historicalAchievements: [],
    achievementsProgress: null,
    state: 'loading',
    isRetrying: false,
    handleRetry: vi.fn(),
    ...overrides,
  }
}

describe('GamificationAchievementsPage', () => {
  afterEach(cleanup)

  beforeEach(() => useGamificationAchievementsPageMock.mockReturnValue(makeController()))

  it('announces the loading state and shows the recoverable error state', () => {
    const { rerender } = render(<GamificationAchievementsPage />)
    expect(screen.getByLabelText('Carregando conquistas')).toBeVisible()

    const handleRetry = vi.fn()
    useGamificationAchievementsPageMock.mockReturnValue(
      makeController({ state: 'error', handleRetry }),
    )
    rerender(<GamificationAchievementsPage />)
    expect(
      screen.getByRole('heading', { name: 'Não foi possível carregar suas conquistas' }),
    ).toBeVisible()
    const retryButton = screen.getByRole('button', { name: 'Tentar novamente' })
    expect(retryButton).toBeEnabled()
    fireEvent.click(retryButton)
    expect(handleRetry).toHaveBeenCalledOnce()
  })

  it('disables the retry action while a background refetch is pending', () => {
    useGamificationAchievementsPageMock.mockReturnValue(
      makeController({ state: 'error', isRetrying: true }),
    )
    render(<GamificationAchievementsPage />)
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('renders the empty state message when the catalog has no entries', () => {
    useGamificationAchievementsPageMock.mockReturnValue(
      makeController({ state: 'empty' }),
    )
    render(<GamificationAchievementsPage />)
    expect(
      screen.getByRole('heading', { name: 'Nenhuma conquista disponível ainda' }),
    ).toBeVisible()
  })

  it('renders the catalog header and the achievement composition grouped by family', () => {
    useGamificationAchievementsPageMock.mockReturnValue(
      makeController({
        achievementsProgress: { obtainedCount: 5, catalogCount: 12 },
        familyGroups,
        state: 'success',
      }),
    )
    render(<GamificationAchievementsPage />)

    expect(screen.getByRole('heading', { level: 2, name: 'Conquistas' })).toBeVisible()
    expect(screen.getByText('5 de 12 obtidas')).toBeVisible()

    const familyHeading = screen.getByRole('heading', { level: 3, name: 'Diagnóstico' })
    expect(familyHeading.closest('section')).toHaveTextContent('1 de 2 obtidas')

    const obtainedCard = screen
      .getByRole('heading', { level: 4, name: 'Primeiro Passo' })
      .closest('article')
    expect(obtainedCard).toHaveTextContent('+25 XP')
    expect(obtainedCard).toHaveTextContent(/Obtida em \d{1,2} jan 2026/)

    const lockedCard = screen
      .getByRole('heading', { name: 'Explorador' })
      .closest('article')
    expect(lockedCard).toHaveTextContent('5 diagnósticos concluídos')
    expect(lockedCard).toHaveTextContent('+75 XP')
    expect(lockedCard).toHaveTextContent('2 de 5 Diagnósticos')
    const fill = lockedCard?.querySelector<HTMLElement>('[aria-hidden="true"] > div')
    expect(fill?.style.width).toBe('40%')
  })

  it('renders a retired-catalog achievement as historical, keyed by its code, in its own section', () => {
    useGamificationAchievementsPageMock.mockReturnValue(
      makeController({
        historicalAchievements: [historicalAchievement],
        state: 'success',
      }),
    )
    render(<GamificationAchievementsPage />)

    expect(screen.getByRole('heading', { name: 'Histórico' })).toBeVisible()
    const historicalHeading = screen.getByRole('heading', { name: 'RETIRED_CODE' })
    const historicalCard = historicalHeading.closest('article')
    expect(historicalCard).toHaveTextContent('1 diagnóstico concluído')
    expect(historicalCard).toHaveTextContent(
      /Histórica · obtida em \d{1,2} (out|nov) 2025/,
    )
  })
})
