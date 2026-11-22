const LANGUAGE_NAMES = new Intl.DisplayNames(['pt-BR'], { type: 'language' })

/**
 * Turns a Curriculum language code (`en-US`, `pt-BR`) into its pt-BR name.
 * A value that is not a language code is shown as it was authored.
 */
export function languageLabel(language: string): string {
  try {
    const name = LANGUAGE_NAMES.of(language.trim())
    if (!name || name === language.trim()) return language
    return name.charAt(0).toLocaleUpperCase('pt-BR') + name.slice(1)
  } catch {
    return language
  }
}
