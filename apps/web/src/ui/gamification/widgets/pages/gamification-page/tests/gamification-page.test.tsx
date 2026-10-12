import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Achievement } from '@/core/gamification/achievement'

import { GamificationPage } from '..'
import {
  type AchievementFamilyGroup,
  type GamificationPageController,
  useGamificationPage,
} from '../use-gamification-page'

vi.mock('../use-gamification-page', () => ({ useGamificationPage: vi.fn() }))

const useGamificationPageMock = vi.mocked(useGamificationPage)

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
  { family: 'diagnosis', achievements: [obtainedAchievement, lockedAchievement] },
]

function makeController(
  overrides: Partial<GamificationPageController> = {},
): GamificationPageController {
  return {
    familyGroups: [],
    historicalAchievements: [],
    profileSummary: null,
    state: 'loading',
    isRetrying: false,
    handleRetry: vi.fn(),
    ...overrides,
  }
}

describe('GamificationPage', () => {
  afterEach(cleanup)

  beforeEach(() => useGamificationPageMock.mockReturnValue(makeController()))

  it('keeps the existing header while loading and shows the recoverable error state', () => {
    const { rerender } = render(<GamificationPage />)
    expect(
      screen.getByRole('heading', { level: 1, name: 'Cada passo merece ser visto.' }),
    ).toBeVisible()
    expect(screen.getByLabelText('Carregando conquistas')).toBeVisible()

    const handleRetry = vi.fn()
    useGamificationPageMock.mockReturnValue(
      makeController({ state: 'error', handleRetry }),
    )
    rerender(<GamificationPage />)
    expect(
      screen.getByRole('heading', { name: 'Não foi possível carregar suas conquistas' }),
    ).toBeVisible()
    const retryButton = screen.getByRole('button', { name: 'Tentar novamente' })
    expect(retryButton).toBeEnabled()
    fireEvent.click(retryButton)
    expect(handleRetry).toHaveBeenCalledOnce()
  })

  it('disables the retry action while a background refetch is pending', () => {
    useGamificationPageMock.mockReturnValue(
      makeController({ state: 'error', isRetrying: true }),
    )
    render(<GamificationPage />)
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('renders the empty state message when the catalog has no entries', () => {
    useGamificationPageMock.mockReturnValue(makeController({ state: 'empty' }))
    render(<GamificationPage />)
    expect(
      screen.getByRole('heading', { name: 'Nenhuma conquista disponível ainda' }),
    ).toBeVisible()
  })

  it('renders the profile summary and real achievement composition grouped by family', () => {
    useGamificationPageMock.mockReturnValue(
      makeController({
        familyGroups,
        profileSummary: { level: 3, totalXp: 640, xpForNextLevel: 360 },
        state: 'success',
      }),
    )
    render(<GamificationPage />)

    expect(screen.getByText('03')).toBeVisible()
    expect(screen.getByText('640 XP')).toBeVisible()
    expect(screen.getByText('360 XP para o próximo nível')).toBeVisible()

    expect(screen.getByRole('heading', { name: 'Diagnóstico' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Primeiro Passo' })).toBeVisible()
    expect(screen.getByText(/Conquistada em/)).toBeVisible()

    const lockedHeading = screen.getByRole('heading', { name: 'Explorador' })
    const lockedCard = lockedHeading.closest('article')
    expect(lockedCard).toHaveTextContent('5 diagnósticos concluídos')
    expect(lockedCard).toHaveTextContent('(2 de 5)')
    expect(lockedCard).toHaveTextContent('Bloqueada')
  })

  it('renders a retired-catalog achievement as historical, keyed by its code, in its own section', () => {
    useGamificationPageMock.mockReturnValue(
      makeController({
        historicalAchievements: [historicalAchievement],
        profileSummary: { level: 1, totalXp: 0, xpForNextLevel: 100 },
        state: 'success',
      }),
    )
    render(<GamificationPage />)

    expect(screen.getByRole('heading', { name: 'Histórico' })).toBeVisible()
    const historicalHeading = screen.getByRole('heading', { name: 'RETIRED_CODE' })
    const historicalCard = historicalHeading.closest('article')
    expect(historicalCard).toHaveTextContent('Histórica')
    expect(historicalCard).toHaveTextContent(/em/)
  })
})
