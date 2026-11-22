import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'

import { EngagementSummary } from '..'
import { useEngagementSummary } from '../use-engagement-summary'

// Counters and entrance motion settle at once, so assertions see final values;
// the animation case opts back into motion explicitly.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-engagement-summary', () => ({
  useEngagementSummary: vi.fn(),
}))

const useEngagementSummaryMock = vi.mocked(useEngagementSummary)

type EngagementSummaryController = ReturnType<typeof useEngagementSummary>

function makeController(
  overrides: Partial<EngagementSummaryController> = {},
): EngagementSummaryController {
  return {
    summary: {
      level: 4,
      totalXp: 850,
      xpForNextLevel: 150,
      levelPercentage: 62,
      currentStreak: 7,
      longestStreak: 12,
    },
    state: 'success',
    isRetrying: false,
    formatXp: (value: number) => new Intl.NumberFormat('pt-BR').format(value),
    handleRetry: vi.fn(),
    ...overrides,
  }
}

describe('EngagementSummary', () => {
  afterEach(() => {
    cleanup()
    vi.mocked(useReducedMotionPreference).mockReturnValue({ prefersReducedMotion: true })
  })

  beforeEach(() => useEngagementSummaryMock.mockReturnValue(makeController()))

  it('renders the level card with XP, missing XP and an accessible progress value', () => {
    render(<EngagementSummary />)

    const card = screen.getByRole('article', { name: 'Engajamento: nível e XP' })
    expect(card).toHaveTextContent('Engajamento')
    expect(card).toHaveTextContent('Nível 4')
    expect(card).toHaveTextContent('850 XP · faltam 150 XP para o nível 5')

    const progress = screen.getByRole('progressbar', { name: 'Progresso para o nível 5' })
    expect(progress).toHaveAttribute('aria-valuenow', '62')
    expect(progress).toHaveAttribute('aria-valuetext', '62% concluído, faltam 150 XP')
  })

  it('renders the streak card with the current streak and the record', () => {
    render(<EngagementSummary />)

    const card = screen.getByRole('article', { name: 'Engajamento: sequência' })
    expect(card).toHaveTextContent('Engajamento')
    expect(card).toHaveTextContent('7 dias')
    expect(card).toHaveTextContent('Sequência atual · recorde de 12 dias')
  })

  it('uses the singular form for a one-day streak and record', () => {
    useEngagementSummaryMock.mockReturnValue(
      makeController({
        summary: {
          level: 1,
          totalXp: 20,
          xpForNextLevel: 80,
          levelPercentage: 20,
          currentStreak: 1,
          longestStreak: 1,
        },
      }),
    )
    render(<EngagementSummary />)

    const card = screen.getByRole('article', { name: 'Engajamento: sequência' })
    expect(card).toHaveTextContent('1 dia')
    expect(card).toHaveTextContent('Sequência atual · recorde de 1 dia')
  })

  it('shows a zero level progress for a new account without inventing values', () => {
    useEngagementSummaryMock.mockReturnValue(
      makeController({
        summary: {
          level: 1,
          totalXp: 0,
          xpForNextLevel: 100,
          levelPercentage: 0,
          currentStreak: 0,
          longestStreak: 0,
        },
      }),
    )
    render(<EngagementSummary />)

    expect(
      screen.getByRole('progressbar', { name: 'Progresso para o nível 2' }),
    ).toHaveAttribute('aria-valuenow', '0')
    expect(screen.getByText('0 dias')).toBeVisible()
  })

  it('counts the level and the streak up to their final values', async () => {
    vi.mocked(useReducedMotionPreference).mockReturnValue({ prefersReducedMotion: false })
    render(<EngagementSummary />)

    await waitFor(
      () => {
        expect(screen.getByText('Nível 4')).toBeInTheDocument()
        expect(screen.getByText('7 dias')).toBeInTheDocument()
      },
      { timeout: 3000 },
    )
  })

  it('announces a loading placeholder for each summary card', () => {
    useEngagementSummaryMock.mockReturnValue(
      makeController({ state: 'loading', summary: null }),
    )
    render(<EngagementSummary />)

    expect(screen.getByLabelText('Carregando nível e XP')).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(screen.getByLabelText('Carregando sequência')).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('marks the Engajamento cards with the latão family only', () => {
    const { container } = render(<EngagementSummary />)

    const markers = container.querySelectorAll('span[aria-hidden="true"].rounded-full')
    expect(markers).toHaveLength(2)
    for (const marker of markers) {
      expect(marker).toHaveClass('bg-latao-fill')
      expect(marker).not.toHaveClass('bg-jade-fill')
    }
  })

  it('shows each unavailable card with its own working retry that disables while retrying', async () => {
    const handleRetry = vi.fn()
    useEngagementSummaryMock.mockReturnValue(
      makeController({ state: 'error', summary: null, handleRetry }),
    )
    const { rerender } = render(<EngagementSummary />)

    const cards = screen.getAllByRole('article')
    expect(cards).toHaveLength(2)
    expect(cards[0]).toHaveTextContent('Nível e XP')
    expect(cards[1]).toHaveTextContent('Sequência de prática')
    for (const card of cards) {
      expect(card).toHaveTextContent('Indisponível no momento.')
      expect(card).toHaveTextContent('Engajamento')
    }
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    const retries = screen.getAllByRole('button', { name: 'Tentar novamente' })
    expect(retries).toHaveLength(2)
    await userEvent.click(retries[1])
    expect(handleRetry).toHaveBeenCalledOnce()

    useEngagementSummaryMock.mockReturnValue(
      makeController({ state: 'error', summary: null, isRetrying: true, handleRetry }),
    )
    rerender(<EngagementSummary />)
    for (const retry of screen.getAllByRole('button', { name: 'Tentar novamente' }))
      expect(retry).toBeDisabled()
  })
})
