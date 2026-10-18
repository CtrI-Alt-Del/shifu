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

  return { formatMonthLabel, formatDayLabel, formatWeekdayLabel }
}

// Calendar dates are plain `YYYY-MM-DD` with no time: parsing them as UTC
// keeps the rendered day from shifting in zones behind Greenwich.
function toUtcDate(isoDate: string): Date {
  return new Date(`${isoDate}T00:00:00Z`)
}
