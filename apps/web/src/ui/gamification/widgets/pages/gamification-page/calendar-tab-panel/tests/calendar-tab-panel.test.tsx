import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PracticeCalendar } from '@/core/gamification/practice-calendar'

import { CalendarTabPanel } from '..'
import {
  type CalendarTabPanelController,
  useCalendarTabPanel,
} from '../use-calendar-tab-panel'

vi.mock('../use-calendar-tab-panel', () => ({ useCalendarTabPanel: vi.fn() }))

const useCalendarTabPanelMock = vi.mocked(useCalendarTabPanel)

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
  overrides: Partial<CalendarTabPanelController> = {},
): CalendarTabPanelController {
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

describe('CalendarTabPanel', () => {
  afterEach(cleanup)

  beforeEach(() => useCalendarTabPanelMock.mockReturnValue(makeController()))

  it('announces the loading state before the calendar resolves', () => {
    useCalendarTabPanelMock.mockReturnValue(
      makeController({ state: 'loading', calendar: null }),
    )
    render(<CalendarTabPanel />)

    expect(screen.getByLabelText('Carregando calendário de prática')).toBeVisible()
  })

  it('shows a recoverable error with a working retry action', async () => {
    const handleRetry = vi.fn()
    useCalendarTabPanelMock.mockReturnValue(
      makeController({ state: 'error', calendar: null, handleRetry }),
    )
    render(<CalendarTabPanel />)

    expect(
      screen.getByRole('heading', { name: 'Não foi possível carregar seu calendário' }),
    ).toBeVisible()
    const retryButton = screen.getByRole('button', { name: 'Tentar novamente' })
    expect(retryButton).toBeEnabled()
    await userEvent.click(retryButton)
    expect(handleRetry).toHaveBeenCalledOnce()
  })

  it('disables the retry action while a refetch is already pending', () => {
    useCalendarTabPanelMock.mockReturnValue(
      makeController({ state: 'error', calendar: null, isRetrying: true }),
    )
    render(<CalendarTabPanel />)

    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('renders the month starting on Monday with each day state labelled', () => {
    render(<CalendarTabPanel />)

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
    render(<CalendarTabPanel />)

    expect(screen.getByRole('button', { name: 'Próximo mês' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Mês anterior' })).toBeEnabled()
  })

  it('disables previous-month navigation at the earliest practice month', () => {
    useCalendarTabPanelMock.mockReturnValue(makeController({ isAtEarliestMonth: true }))
    render(<CalendarTabPanel />)

    expect(screen.getByRole('button', { name: 'Mês anterior' })).toBeDisabled()
  })

  it('moves to the previous month from the keyboard', async () => {
    const goToPreviousMonth = vi.fn()
    useCalendarTabPanelMock.mockReturnValue(makeController({ goToPreviousMonth }))
    render(<CalendarTabPanel />)

    screen.getByRole('button', { name: 'Mês anterior' }).focus()
    await userEvent.keyboard('{Enter}')

    expect(goToPreviousMonth).toHaveBeenCalledOnce()
  })

  it('confirms only the date of a selected practice day', () => {
    useCalendarTabPanelMock.mockReturnValue(
      makeController({ selectedDay: { day: '2026-09-09', state: 'current-streak' } }),
    )
    render(<CalendarTabPanel />)

    const confirmation = screen.getByText(/Houve prática neste dia/)
    expect(confirmation).toBeVisible()
    expect(confirmation).toHaveTextContent('9 de setembro')
    expect(confirmation).not.toHaveTextContent(/XP/)
    expect(confirmation).not.toHaveTextContent(/[Aa]tividade/)
  })

  it('selects a day when it is activated', async () => {
    const handleSelectDay = vi.fn()
    useCalendarTabPanelMock.mockReturnValue(makeController({ handleSelectDay }))
    render(<CalendarTabPanel />)

    await userEvent.click(
      screen.getByRole('button', { name: /9 de setembro, dia da sequência atual/ }),
    )

    expect(handleSelectDay).toHaveBeenCalledWith({
      day: '2026-09-09',
      state: 'current-streak',
    })
  })

  it('renders the streak context and the five-state legend', () => {
    render(<CalendarTabPanel />)

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
})
