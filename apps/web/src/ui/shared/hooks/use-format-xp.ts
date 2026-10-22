const XP_FORMATTER = new Intl.NumberFormat('pt-BR')

export function useFormatXp() {
  function formatXp(value: number): string {
    return XP_FORMATTER.format(value)
  }

  return { formatXp }
}
