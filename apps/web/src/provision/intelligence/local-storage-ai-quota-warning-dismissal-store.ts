import type { AiQuotaWarningDismissalStore } from '@/core/intelligence/ai-quota-warning-dismissal-store'

const DISMISSED_VALUE = '1'

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
        try {
          return window.localStorage.getItem(dismissalKey(accountId, monthKey)) !== null
        } catch {
          return false
        }
      },
      dismiss(accountId, monthKey) {
        window.localStorage.setItem(dismissalKey(accountId, monthKey), DISMISSED_VALUE)
      },
    }
  }
