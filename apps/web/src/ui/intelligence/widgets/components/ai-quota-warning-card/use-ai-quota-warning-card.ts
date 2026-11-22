import { useEffect, useState } from 'react'

import { aiQuotaMonthKey } from '@/core/intelligence/ai-quota-usage'
import {
  clearAiQuotaWarningDismissals,
  isAccountDataRevoked,
  LocalStorageAiQuotaWarningDismissalStore,
} from '@/provision/intelligence/local-storage-ai-quota-warning-dismissal-store'
import { aiQuotaWarningMessage } from '@/ui/intelligence/constants/ai-quota-presentation'

import type { AiQuotaWarningCardProps } from '.'

const DISMISSAL_STORE = LocalStorageAiQuotaWarningDismissalStore()

export function useAiQuotaWarningCard({
  accountId,
  percentage,
  renewsOn,
}: AiQuotaWarningCardProps) {
  const monthKey = aiQuotaMonthKey(renewsOn)
  const dismissalKey = `${accountId}:${monthKey}`
  // Set even when the write fails, so the warning stays hidden for this session.
  const [sessionDismissedKey, setSessionDismissedKey] = useState<string | null>(null)
  const [revokedAccountId, setRevokedAccountId] = useState<string | null>(null)
  useEffect(() => {
    function handleStorage(event: StorageEvent) {
      if (
        event.key === `shifu:account-data-revoked:${accountId}` &&
        event.newValue === '1'
      ) {
        clearAiQuotaWarningDismissals(accountId)
        setRevokedAccountId(accountId)
      }
    }

    function handleAccountDataRevoked(event: Event) {
      const detail = (event as CustomEvent<{ accountId?: unknown }>).detail
      if (detail?.accountId === accountId) {
        clearAiQuotaWarningDismissals(accountId)
        setRevokedAccountId(accountId)
      }
    }

    window.addEventListener('storage', handleStorage)
    window.addEventListener('shifu:account-data-revoked', handleAccountDataRevoked)
    return () => {
      window.removeEventListener('storage', handleStorage)
      window.removeEventListener('shifu:account-data-revoked', handleAccountDataRevoked)
    }
  }, [accountId])
  const isDismissed =
    revokedAccountId === accountId ||
    isAccountDataRevoked(accountId) ||
    sessionDismissedKey === dismissalKey ||
    DISMISSAL_STORE.isDismissed(accountId, monthKey)
  const message = aiQuotaWarningMessage(percentage, renewsOn)

  function handleDismiss() {
    try {
      DISMISSAL_STORE.dismiss(accountId, monthKey)
    } catch {
      setSessionDismissedKey(dismissalKey)
      return
    }
    setSessionDismissedKey(dismissalKey)
  }

  return { isDismissed, message, handleDismiss }
}
