import { useState } from 'react'

import type { CalendarDay } from '@/core/gamification/practice-calendar'

import { usePracticeCalendarQuery } from './use-practice-calendar-query'

export type CalendarTabPanelState = 'loading' | 'success' | 'error'

type ViewedMonth = { year: number; month: number }

export function useCalendarTabPanel() {
  const [viewedMonth, setViewedMonth] = useState<ViewedMonth>(currentMonth)
  const [selectedDay, setSelectedDay] = useState<CalendarDay | null>(null)
  const {
    calendar,
    calendarError,
    isLoadingCalendar,
    isFetchingCalendar,
    refetchCalendar,
  } = usePracticeCalendarQuery(viewedMonth.year, viewedMonth.month)

  const state: CalendarTabPanelState = isLoadingCalendar
    ? 'loading'
    : calendarError || !calendar
      ? 'error'
      : 'success'

  const today = currentMonth()
  const isAtCurrentMonth =
    viewedMonth.year === today.year && viewedMonth.month === today.month
  const earliest = calendar?.earliestPracticeDate ?? null
  const isAtEarliestMonth =
    earliest !== null &&
    viewedMonth.year === Number(earliest.slice(0, 4)) &&
    viewedMonth.month === Number(earliest.slice(5, 7))

  function goToPreviousMonth() {
    if (isAtEarliestMonth) return
    setSelectedDay(null)
    setViewedMonth((previous) => shiftMonth(previous, -1))
  }

  function goToNextMonth() {
    if (isAtCurrentMonth) return
    setSelectedDay(null)
    setViewedMonth((previous) => shiftMonth(previous, 1))
  }

  function handleSelectDay(day: CalendarDay) {
    setSelectedDay(day.state === 'neutral' ? null : day)
  }

  return {
    viewedMonth,
    calendar,
    selectedDay,
    state,
    isAtCurrentMonth,
    isAtEarliestMonth,
    isRetrying: isFetchingCalendar && !isLoadingCalendar,
    goToPreviousMonth,
    goToNextMonth,
    handleSelectDay,
    handleRetry: () => void refetchCalendar(),
  }
}

export type CalendarTabPanelController = ReturnType<typeof useCalendarTabPanel>

function currentMonth(): ViewedMonth {
  const now = new Date()
  return { year: now.getFullYear(), month: now.getMonth() + 1 }
}

function shiftMonth(value: ViewedMonth, offset: number): ViewedMonth {
  const shifted = new Date(Date.UTC(value.year, value.month - 1 + offset, 1))
  return { year: shifted.getUTCFullYear(), month: shifted.getUTCMonth() + 1 }
}
