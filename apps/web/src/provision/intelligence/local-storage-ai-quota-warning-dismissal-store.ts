import type { AiQuotaWarningDismissalStore } from '@/core/intelligence/ai-quota-warning-dismissal-store'

const DISMISSED_VALUE = '1'
const ACCOUNT_DATA_REVOKED_PREFIX = 'shifu:account-data-revoked:'

export function isAccountDataRevoked(accountId: string): boolean {
  try {
    const isRevoked =
      window.localStorage.getItem(`${ACCOUNT_DATA_REVOKED_PREFIX}${accountId}`) ===
      DISMISSED_VALUE
    if (isRevoked) clearAiQuotaWarningDismissals(accountId)
    return isRevoked
  } catch {
    return false
  }
}

export function clearAiQuotaWarningDismissals(accountId: string): void {
  const prefix = `shifu:ai-quota-warning-dismissed:${accountId}:`
  try {
    const matchingKeys: string[] = []
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index)
      if (key?.startsWith(prefix)) matchingKeys.push(key)
    }
    for (const key of matchingKeys) window.localStorage.removeItem(key)
  } catch {
    // The persistent revocation marker still prevents future reads when storage allows it.
  }
}

function dismissalKey(accountId: string, monthKey: string) {
  return `shifu:ai-quota-warning-dismissed:${accountId}:${monthKey}`
}

/**
 * A failed read reports the warning as not dismissed. A failed write throws so the
 * caller can hide the warning for the current session only.
 */
export const LocalStorageAiQuotaWarningDismissalStore =
  (): AiQuotaWarningDismissalStore => {
    return {
      isDismissed(accountId, monthKey) {
        if (isAccountDataRevoked(accountId)) return true
        try {
          return window.localStorage.getItem(dismissalKey(accountId, monthKey)) !== null
        } catch {
          return false
        }
      },
      dismiss(accountId, monthKey) {
        if (isAccountDataRevoked(accountId)) return
        window.localStorage.setItem(dismissalKey(accountId, monthKey), DISMISSED_VALUE)
      },
    }
  }
