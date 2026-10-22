import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useFormatDate } from '../use-format-date'

describe('useFormatDate', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('formats the month label with a capitalized name and the year', () => {
    const { result } = renderHook(() => useFormatDate())

    expect(result.current.formatMonthLabel(2026, 9)).toBe('Setembro 2026')
  })

  it('formats a calendar day label in UTC', () => {
    const { result } = renderHook(() => useFormatDate())

    expect(result.current.formatDayLabel('2026-09-13')).toBe('13 de setembro')
  })

  it('formats a calendar weekday label in UTC', () => {
    const { result } = renderHook(() => useFormatDate())

    expect(result.current.formatWeekdayLabel('2026-09-13')).toBe(
      'domingo, 13 de setembro',
    )
  })

  it('formats an instant as a short date without the trailing dot', () => {
    const { result } = renderHook(() => useFormatDate())

    expect(result.current.formatShortDate('2026-09-13T12:00:00Z')).not.toContain('.')
  })

  it('falls back to an empty part when a formatter omits a date segment', () => {
    vi.spyOn(Intl.DateTimeFormat.prototype, 'formatToParts').mockReturnValue([
      { type: 'day', value: '13' },
    ])

    const { result } = renderHook(() => useFormatDate())

    expect(result.current.formatShortDate('2026-09-13T12:00:00Z')).toBe('13  ')
  })
})
