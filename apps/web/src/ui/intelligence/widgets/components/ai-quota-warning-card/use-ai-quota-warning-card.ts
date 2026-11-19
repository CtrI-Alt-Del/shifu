import { useState } from 'react'

import { aiQuotaMonthKey } from '@/core/intelligence/ai-quota-usage'
import { LocalStorageAiQuotaWarningDismissalStore } from '@/provision/intelligence/local-storage-ai-quota-warning-dismissal-store'
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
  const isDismissed =
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
