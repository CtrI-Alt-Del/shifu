import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PracticeCalendar } from '@/core/gamification/practice-calendar'

import { GamificationCalendarPage } from '..'
import {
  type GamificationCalendarPageController,
  useGamificationCalendarPage,
} from '../use-gamification-calendar-page'

// Entrance motion and counters settle at once, so assertions see the final
// state; the shared components own their own animated cases.
vi.mock('motion/react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('motion/react')>()),
  useReducedMotion: vi.fn(() => true),
}))
vi.mock('../use-gamification-calendar-page', () => ({
  useGamificationCalendarPage: vi.fn(),
}))

const useGamificationCalendarPageMock = vi.mocked(useGamificationCalendarPage)

const calendar: PracticeCalendar = {
  year: 2026,
  month: 9,
  today: '2026-09-11',
  days: [
    { day: '2026-09-01', state: 'neutral' },
    { day: '2026-09-02', state: 'practiced' },
    { day: '2026-09-03', state: 'missed' },
    { day: '2026-09-09', state: 'current-streak' },
    { day: '2026-09-10', state: 'current-streak' },
    { day: '2026-09-11', state: 'today-pending' },
  ],
  streak: { current: 2, longest: 5 },
  earliestPracticeDate: '2026-09-02',
}

function makeController(
  overrides: Partial<GamificationCalendarPageController> = {},
): GamificationCalendarPageController {
  return {
    viewedMonth: { year: 2026, month: 9 },
    calendar,
    selectedDay: null,
    state: 'success',
    isAtCurrentMonth: true,
    isAtEarliestMonth: false,
    isRetrying: false,
    goToPreviousMonth: vi.fn(),
    goToNextMonth: vi.fn(),
    handleSelectDay: vi.fn(),
    handleRetry: vi.fn(),
    ...overrides,
  }
}

describe('GamificationCalendarPage', () => {
  afterEach(cleanup)

  beforeEach(() => useGamificationCalendarPageMock.mockReturnValue(makeController()))

  it('announces the loading state before the calendar resolves', () => {
    useGamificationCalendarPageMock.mockReturnValue(
      makeController({ state: 'loading', calendar: null }),
    )
    render(<GamificationCalendarPage />)

    expect(screen.getByLabelText('Carregando calendário de prática')).toBeVisible()
  })

  it('shows a recoverable error with a working retry action', async () => {
    const handleRetry = vi.fn()
    useGamificationCalendarPageMock.mockReturnValue(
      makeController({ state: 'error', calendar: null, handleRetry }),
    )
    render(<GamificationCalendarPage />)

    expect(
      screen.getByRole('heading', { name: 'Não foi possível carregar seu calendário' }),
    ).toBeVisible()
    const retryButton = screen.getByRole('button', { name: 'Tentar novamente' })
    expect(retryButton).toBeEnabled()
    await userEvent.click(retryButton)
    expect(handleRetry).toHaveBeenCalledOnce()
  })

  it('disables the retry action while a refetch is already pending', () => {
    useGamificationCalendarPageMock.mockReturnValue(
      makeController({ state: 'error', calendar: null, isRetrying: true }),
    )
    render(<GamificationCalendarPage />)

    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('renders the month starting on Monday with each day state labelled', () => {
    render(<GamificationCalendarPage />)

    expect(screen.getByRole('heading', { name: /Setembro 2026/ })).toBeVisible()
    const weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    for (const label of weekdays) expect(screen.getByText(label)).toBeVisible()

    expect(
      screen.getByRole('button', { name: /2 de setembro, dia de prática/ }),
    ).toBeVisible()
    expect(
      screen.getByRole('button', { name: /3 de setembro, dia encerrado sem prática/ }),
    ).toBeVisible()
    expect(
      screen.getByRole('button', { name: /9 de setembro, dia da sequência atual/ }),
    ).toBeVisible()
    expect(
      screen.getByRole('button', {
        name: /11 de setembro, hoje, prática ainda pendente/,
      }),
    ).toBeVisible()
    expect(
      screen.getByRole('button', { name: /1 de setembro, sem registro/ }),
    ).toBeVisible()
  })

  it('disables next-month navigation on the current month', () => {
    render(<GamificationCalendarPage />)

    expect(screen.getByRole('button', { name: 'Próximo mês' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Mês anterior' })).toBeEnabled()
  })

  it('disables previous-month navigation at the earliest practice month', () => {
    useGamificationCalendarPageMock.mockReturnValue(
      makeController({ isAtEarliestMonth: true }),
    )
    render(<GamificationCalendarPage />)

    expect(screen.getByRole('button', { name: 'Mês anterior' })).toBeDisabled()
  })

  it('moves to the previous month from the keyboard', async () => {
    const goToPreviousMonth = vi.fn()
    useGamificationCalendarPageMock.mockReturnValue(makeController({ goToPreviousMonth }))
    render(<GamificationCalendarPage />)

    screen.getByRole('button', { name: 'Mês anterior' }).focus()
    await userEvent.keyboard('{Enter}')

    expect(goToPreviousMonth).toHaveBeenCalledOnce()
  })

  it('confirms only the date of a selected practice day', () => {
    useGamificationCalendarPageMock.mockReturnValue(
      makeController({ selectedDay: { day: '2026-09-09', state: 'current-streak' } }),
    )
    render(<GamificationCalendarPage />)

    const confirmation = screen.getByText(/Houve prática neste dia/)
    expect(confirmation).toBeVisible()
    expect(confirmation).toHaveTextContent('9 de setembro')
    expect(confirmation).not.toHaveTextContent(/XP/)
    expect(confirmation).not.toHaveTextContent(/[Aa]tividade/)
  })

  it('selects a day when it is activated', async () => {
    const handleSelectDay = vi.fn()
    useGamificationCalendarPageMock.mockReturnValue(makeController({ handleSelectDay }))
    render(<GamificationCalendarPage />)

    await userEvent.click(
      screen.getByRole('button', { name: /9 de setembro, dia da sequência atual/ }),
    )

    expect(handleSelectDay).toHaveBeenCalledWith({
      day: '2026-09-09',
      state: 'current-streak',
    })
  })

  it('renders the streak context and the five-state legend', () => {
    render(<GamificationCalendarPage />)

    const streakSection = screen.getByRole('region', { name: 'Sua constância' })
    expect(streakSection).toBeVisible()
    expect(within(streakSection).getByText('2')).toBeVisible()
    expect(within(streakSection).getByText('dias seguidos')).toBeVisible()
    expect(screen.getByText('Maior sequência: 5 dias')).toBeVisible()
    expect(screen.getByText('Pratique hoje para manter sua sequência.')).toBeVisible()

    expect(screen.getByRole('heading', { name: 'Estados dos dias' })).toBeVisible()
    const legendLabels = [
      'Neutro',
      'Dia de prática',
      'Sequência atual',
      'Sem prática',
      'Hoje pendente',
    ]
    for (const label of legendLabels) expect(screen.getByText(label)).toBeVisible()
  })

  it('invites a learner with no practice yet to practice today', () => {
    useGamificationCalendarPageMock.mockReturnValue(
      makeController({
        calendar: {
          ...calendar,
          days: [
            { day: '2026-09-10', state: 'neutral' },
            { day: '2026-09-11', state: 'neutral' },
          ],
          streak: { current: 0, longest: 0 },
          earliestPracticeDate: null,
        },
      }),
    )
    render(<GamificationCalendarPage />)

    expect(screen.getByText('Pratique hoje para manter sua sequência.')).toBeVisible()
    expect(screen.queryByText('Você já praticou hoje.')).not.toBeInTheDocument()
  })

  it('confirms the practice once today already counts', () => {
    useGamificationCalendarPageMock.mockReturnValue(
      makeController({
        calendar: {
          ...calendar,
          days: [
            { day: '2026-09-10', state: 'current-streak' },
            { day: '2026-09-11', state: 'current-streak' },
          ],
        },
      }),
    )
    render(<GamificationCalendarPage />)

    expect(screen.getByText('Você já praticou hoje.')).toBeVisible()
  })
})
