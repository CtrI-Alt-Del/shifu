export const AI_QUOTA_STATUSES = ['normal', 'near_limit', 'blocked'] as const
export type AiQuotaStatus = (typeof AI_QUOTA_STATUSES)[number]

export type AiQuotaUsage = {
  percentage: number
  status: AiQuotaStatus
  /** ISO 8601 date of the next renewal, always the first day of a month. */
  renewsOn: string
}

/** One reading: the account id only keys the local warning dismissal. */
export type AiQuotaUsageReading = { usage: AiQuotaUsage; accountId: string }

export const AI_QUOTA_EXHAUSTED_CODE = 'ai_quota_exhausted'

export type AiQuotaExhaustedFailure = { kind: 'quota-exhausted' }

/** Result of a Mentor start: a quota refusal travels as data, other errors still throw. */
export type MentorStartResult<T> =
  | { ok: true; value: T }
  | { ok: false; failure: AiQuotaExhaustedFailure }

const MONTH_KEY_PATTERN = /^(\d{4})-(\d{2})/

/** `YYYY-MM` of the month before the renewal date, which is the quota month. */
export function aiQuotaMonthKey(renewsOn: string): string {
  const match = MONTH_KEY_PATTERN.exec(renewsOn)
  if (!match) return ''
  const year = Number(match[1])
  const month = Number(match[2])
  const previousYear = month === 1 ? year - 1 : year
  const previousMonth = month === 1 ? 12 : month - 1
  return `${String(previousYear).padStart(4, '0')}-${String(previousMonth).padStart(2, '0')}`
}

export function isAiQuotaExhaustedFailure(
  value: unknown,
): value is AiQuotaExhaustedFailure {
  return (
    typeof value === 'object' &&
    value !== null &&
    'kind' in value &&
    value.kind === 'quota-exhausted'
  )
}

/** The server refusal wins over a stale reading, so a refusal alone blocks. */
export function checkAiQuotaBlocked(
  usage: AiQuotaUsage | null,
  hasRefusal: boolean,
): boolean {
  return hasRefusal || usage?.status === 'blocked'
}
