import { checkAiQuotaBlocked } from '@/core/intelligence/ai-quota-usage'
import {
  type AiQuotaSurface,
  aiQuotaBlockedMessage,
} from '@/ui/intelligence/constants/ai-quota-presentation'

import { useAiQuotaUsageQuery } from './use-ai-quota-usage-query'

/**
 * Single answer to "is AI blocked here?" for every surface that starts AI work.
 * `hasRefusal` is true when a start already returned `quota-exhausted` on this
 * screen. The refusal wins over a stale reading, and a failed reading never blocks.
 * Each surface asks for its own blocked message, which names what comes back.
 */
export function useAiQuotaBlock(hasRefusal = false) {
  const { aiQuotaUsage, aiQuotaAccountId } = useAiQuotaUsageQuery()

  const isAiQuotaBlocked = checkAiQuotaBlocked(aiQuotaUsage, hasRefusal)
  const isAiQuotaNearLimit = !isAiQuotaBlocked && aiQuotaUsage?.status === 'near_limit'
  const aiQuotaPercentage = aiQuotaUsage?.percentage ?? null
  const aiQuotaRenewsOn = aiQuotaUsage?.renewsOn ?? null
  const aiQuotaBlockedRole = hasRefusal ? 'alert' : 'status'

  function getAiQuotaBlockedMessage(surface: AiQuotaSurface) {
    return aiQuotaBlockedMessage(surface, aiQuotaRenewsOn)
  }

  return {
    isAiQuotaBlocked,
    isAiQuotaNearLimit,
    getAiQuotaBlockedMessage,
    aiQuotaBlockedRole,
    aiQuotaAccountId,
    aiQuotaPercentage,
    aiQuotaRenewsOn,
  } as const
}
