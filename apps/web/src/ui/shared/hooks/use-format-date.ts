// `month: 'long', year: 'numeric'` yields "outubro de 2026" in pt-BR; the
// design reference renders "Outubro 2026", so the year is appended separately.
const MONTH_NAME_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  month: 'long',
  timeZone: 'UTC',
})

const DAY_LABEL_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

const WEEKDAY_LABEL_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

// A grant is an instant, not a calendar date, so it is formatted in the
// viewer's own zone rather than pinned to UTC like the formatters above.
const SHORT_DATE_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

export function useFormatDate() {
  function formatMonthLabel(year: number, month: number): string {
    const name = MONTH_NAME_FORMATTER.format(new Date(Date.UTC(year, month - 1, 1)))
    return `${name.charAt(0).toUpperCase()}${name.slice(1)} ${year}`
  }

  function formatDayLabel(isoDate: string): string {
    return DAY_LABEL_FORMATTER.format(toUtcDate(isoDate))
  }

  function formatWeekdayLabel(isoDate: string): string {
    return WEEKDAY_LABEL_FORMATTER.format(toUtcDate(isoDate))
  }

  // pt-BR renders the short month as "set." with a trailing dot; the design
  // reference writes "13 set 2026", so the parts are composed by hand.
  function formatShortDate(isoDateTime: string): string {
    const parts = SHORT_DATE_FORMATTER.formatToParts(new Date(isoDateTime))
    const partValue = (type: Intl.DateTimeFormatPartTypes) =>
      parts.find((part) => part.type === type)?.value ?? ''
    const month = partValue('month').replace('.', '')
    return `${partValue('day')} ${month} ${partValue('year')}`
  }

  return { formatMonthLabel, formatDayLabel, formatWeekdayLabel, formatShortDate }
}

// Calendar dates are plain `YYYY-MM-DD` with no time: parsing them as UTC
// keeps the rendered day from shifting in zones behind Greenwich.
function toUtcDate(isoDate: string): Date {
  return new Date(`${isoDate}T00:00:00Z`)
}
