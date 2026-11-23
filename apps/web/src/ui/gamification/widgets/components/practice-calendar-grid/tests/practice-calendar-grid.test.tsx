import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CalendarDay } from '@/core/gamification/practice-calendar'

import { PracticeCalendarGrid } from '..'

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))

const days: CalendarDay[] = [
  { day: '2026-11-02', state: 'practiced' },
  { day: '2026-11-03', state: 'missed' },
  { day: '2026-11-04', state: 'current-streak' },
  { day: '2026-11-05', state: 'today-pending' },
  { day: '2026-11-06', state: 'neutral' },
]

describe('PracticeCalendarGrid', () => {
  afterEach(cleanup)

  it('renders selectable day buttons named by date and state when a handler is given', async () => {
    const onSelectDay = vi.fn()
    render(
      <PracticeCalendarGrid
        days={days}
        onSelectDay={onSelectDay}
        selectedDay={days[1]}
      />,
    )

    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(5)
    expect(buttons[0]).toHaveAccessibleName(
      'segunda-feira, 2 de novembro, dia de prática',
    )
    expect(buttons[1]).toHaveAttribute('aria-current', 'date')
    expect(buttons[0]).not.toHaveAttribute('aria-current')

    await userEvent.click(buttons[2])
    expect(onSelectDay).toHaveBeenCalledWith(days[2])
  })

  it('renders non-interactive days with their date and state as text when no handler is given', () => {
    render(<PracticeCalendarGrid days={days} />)

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(
      screen.getByText('segunda-feira, 2 de novembro, dia de prática'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('terça-feira, 3 de novembro, dia encerrado sem prática'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('quarta-feira, 4 de novembro, dia da sequência atual'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('quinta-feira, 5 de novembro, hoje, prática ainda pendente'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('sexta-feira, 6 de novembro, sem registro'),
    ).toBeInTheDocument()
  })

  it('keeps the day number and state glyph visible inside a non-interactive day', () => {
    render(<PracticeCalendarGrid days={days} />)

    const cell = screen
      .getByText('segunda-feira, 2 de novembro, dia de prática')
      .closest('div') as HTMLElement
    expect(within(cell).getByText('2')).toBeVisible()
  })

  it('keeps the regular grid at 64 px with a glyph per state and no compact styling', () => {
    render(<PracticeCalendarGrid days={days} />)

    const cell = screen
      .getByText('segunda-feira, 2 de novembro, dia de prática')
      .closest('div') as HTMLElement
    expect(cell).toHaveClass('h-16', 'flex-col')
    expect(cell.querySelector('svg')).not.toBeNull()
    expect(cell).not.toHaveClass('h-10')
  })

  it('opens the weekday header on Monday', () => {
    render(<PracticeCalendarGrid days={[{ day: '2026-11-04', state: 'neutral' }]} />)

    expect(
      screen
        .getAllByText(/^(Seg|Ter|Qua|Qui|Sex|Sáb|Dom)$/)
        .map((node) => node.textContent),
    ).toEqual(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'])
  })
  it('draws compact 40 px cells by fill and border with the day number only, still Monday-first', () => {
    render(<PracticeCalendarGrid compact days={days} />)

    const streak = screen
      .getByText('quarta-feira, 4 de novembro, dia da sequência atual')
      .closest('div') as HTMLElement
    const today = screen
      .getByText('quinta-feira, 5 de novembro, hoje, prática ainda pendente')
      .closest('div') as HTMLElement
    const practiced = screen
      .getByText('segunda-feira, 2 de novembro, dia de prática')
      .closest('div') as HTMLElement

    for (const cell of [streak, today, practiced]) expect(cell).toHaveClass('h-10')
    expect(streak).toHaveClass('bg-latao-fill')
    expect(practiced).toHaveClass('bg-latao-tint', 'border-latao-solid/50!')
    expect(today).toHaveClass('border-dashed')
    const missed = screen
      .getByText('terça-feira, 3 de novembro, dia encerrado sem prática')
      .closest('div') as HTMLElement
    const neutral = screen
      .getByText('sexta-feira, 6 de novembro, sem registro')
      .closest('div') as HTMLElement
    expect(missed).toHaveClass('border', 'border-control-border!')
    expect(neutral.className).not.toMatch(/\bborder\b|bg-latao/)
    expect(within(streak).getByText('4')).toBeVisible()
    expect(streak.querySelector('svg')).toBeNull()
    expect(
      screen
        .getAllByText(/^(Seg|Ter|Qua|Qui|Sex|Sáb|Dom)$/)
        .map((node) => node.textContent)[0],
    ).toBe('Seg')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
