import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PracticeCalendar } from '@/core/gamification/practice-calendar'

import { useGamificationCalendarPage } from '../use-gamification-calendar-page'
import { usePracticeCalendarQuery } from '../use-practice-calendar-query'

vi.mock('../use-practice-calendar-query', () => ({
  usePracticeCalendarQuery: vi.fn(),
}))

const usePracticeCalendarQueryMock = vi.mocked(usePracticeCalendarQuery)

const NOW = new Date('2026-09-15T12:00:00Z')

function calendarWith(earliestPracticeDate: string | null): PracticeCalendar {
  return {
    year: 2026,
    month: 9,
    today: '2026-09-15',
    days: [{ day: '2026-09-02', state: 'practiced' }],
    streak: { current: 0, longest: 3 },
    earliestPracticeDate,
  }
}

function mockQuery(calendar: PracticeCalendar | null) {
  usePracticeCalendarQueryMock.mockReturnValue({
    calendar,
    calendarError: null,
    isLoadingCalendar: false,
    isFetchingCalendar: false,
    refetchCalendar: vi.fn(),
  } as unknown as ReturnType<typeof usePracticeCalendarQuery>)
}

describe('useGamificationCalendarPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW)
    mockQuery(calendarWith('2026-08-02'))
  })

  afterEach(() => vi.useRealTimers())

  it('opens on the current month', () => {
    const { result } = renderHook(() => useGamificationCalendarPage())

    expect(result.current.viewedMonth).toEqual({ year: 2026, month: 9 })
    expect(result.current.isAtCurrentMonth).toBe(true)
  })

  it('moves to the previous month and reports leaving the current month', () => {
    const { result } = renderHook(() => useGamificationCalendarPage())

    act(() => result.current.goToPreviousMonth())

    expect(result.current.viewedMonth).toEqual({ year: 2026, month: 8 })
    expect(result.current.isAtCurrentMonth).toBe(false)
  })

  it('rolls the year backwards across January', () => {
    vi.setSystemTime(new Date('2026-01-10T12:00:00Z'))
    const { result } = renderHook(() => useGamificationCalendarPage())

    act(() => result.current.goToPreviousMonth())

    expect(result.current.viewedMonth).toEqual({ year: 2025, month: 12 })
  })

  it('refuses to advance past the current month', () => {
    const { result } = renderHook(() => useGamificationCalendarPage())

    act(() => result.current.goToNextMonth())

    expect(result.current.viewedMonth).toEqual({ year: 2026, month: 9 })
  })

  it('refuses to go below the earliest practice month', () => {
    mockQuery(calendarWith('2026-09-02'))
    const { result } = renderHook(() => useGamificationCalendarPage())

    expect(result.current.isAtEarliestMonth).toBe(true)
    act(() => result.current.goToPreviousMonth())

    expect(result.current.viewedMonth).toEqual({ year: 2026, month: 9 })
  })

  it('allows navigating back when no practice day is recorded yet', () => {
    mockQuery(calendarWith(null))
    const { result } = renderHook(() => useGamificationCalendarPage())

    expect(result.current.isAtEarliestMonth).toBe(false)
  })

  it('clears the selected day when the viewed month changes', () => {
    const { result } = renderHook(() => useGamificationCalendarPage())

    act(() => result.current.handleSelectDay({ day: '2026-09-02', state: 'practiced' }))
    expect(result.current.selectedDay).toEqual({
      day: '2026-09-02',
      state: 'practiced',
    })

    act(() => result.current.goToPreviousMonth())
    expect(result.current.selectedDay).toBeNull()
  })

  it('does not select a day that has no record', () => {
    const { result } = renderHook(() => useGamificationCalendarPage())

    act(() => result.current.handleSelectDay({ day: '2026-09-20', state: 'neutral' }))

    expect(result.current.selectedDay).toBeNull()
  })
})
