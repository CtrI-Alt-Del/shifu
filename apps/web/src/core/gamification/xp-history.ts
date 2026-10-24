export type XpSource =
  | 'activity'
  | 'diagnosis'
  | 'competency-mastery'
  | 'skill-completion'
  | 'achievement'

export type XpHistoryEntry = {
  id: string
  amount: number
  source: XpSource
  title: string
  detail: string
  occurredAt: string
  grantedAt: string
}

export type XpHistory = {
  totalXp: number
  entries: XpHistoryEntry[]
}
