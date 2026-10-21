import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useFormatDate } from '../use-format-date'

describe('useFormatDate', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('formats month, day and weekday labels in pt-BR', () => {
    const { result } = renderHook(() => useFormatDate())

    expect(result.current.formatMonthLabel(2026, 10)).toBe('Outubro 2026')
    expect(result.current.formatDayLabel('2026-10-21')).toBe('21 de outubro')
    expect(result.current.formatWeekdayLabel('2026-10-21')).toBe(
      'quarta-feira, 21 de outubro',
    )
  })

  it('formats a short date without the trailing month dot', () => {
    const { result } = renderHook(() => useFormatDate())

    expect(result.current.formatShortDate('2026-09-13T12:00:00Z')).toBe('13 set 2026')
  })

  it('falls back to an empty part when a date-format part is absent', () => {
    vi.spyOn(Intl.DateTimeFormat.prototype, 'formatToParts').mockReturnValueOnce([
      { type: 'day', value: '13' },
      { type: 'year', value: '2026' },
    ])
    const { result } = renderHook(() => useFormatDate())

    expect(result.current.formatShortDate('2026-09-13T12:00:00Z')).toBe('13  2026')
  })
})
