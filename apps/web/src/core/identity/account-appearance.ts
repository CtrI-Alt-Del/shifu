export const ACCOUNT_APPEARANCES = ['dark', 'light', 'system'] as const

export type AccountAppearance = (typeof ACCOUNT_APPEARANCES)[number]
