const DATE_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

const TIME_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
})

// pt-BR renders "4 de out. de 2026"; the design renders "4 out 2026".
function formatDate(date: Date): string {
  return DATE_FORMATTER.format(date).replaceAll(' de ', ' ').replace('.', '')
}

export function useFormatInstant() {
  function formatShortDate(isoInstant: string): string {
    return formatDate(new Date(isoInstant))
  }

  function formatDateTime(isoInstant: string): string {
    const date = new Date(isoInstant)
    return `${formatDate(date)}, às ${TIME_FORMATTER.format(date)}`
  }

  return { formatShortDate, formatDateTime }
}
