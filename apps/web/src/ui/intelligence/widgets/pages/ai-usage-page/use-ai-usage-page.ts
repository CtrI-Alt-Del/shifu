import type { AiQuotaStatus, AiQuotaUsage } from '@/core/intelligence/ai-quota-usage'
import { formatAiQuotaRenewalDate } from '@/ui/intelligence/constants/ai-quota-presentation'
import { useAiQuotaUsageQuery } from '@/ui/intelligence/hooks/use-ai-quota-usage-query'

const NORMAL_SENTENCE = 'O Mentor e o planejamento assistido estão disponíveis.'
const NEAR_LIMIT_SENTENCE =
  'Perto do limite. Quando a cota acabar, o Mentor e o planejamento assistido pausam até a renovação.'

function blockedSentence(renewsOn: string): string {
  return `Cota esgotada. O Mentor e o planejamento assistido voltam em ${formatAiQuotaRenewalDate(renewsOn)}. Seus Objetivos e Atividades continuam disponíveis.`
}

function statusSentenceFor(usage: AiQuotaUsage): string {
  const sentences: Record<AiQuotaStatus, string> = {
    normal: NORMAL_SENTENCE,
    near_limit: NEAR_LIMIT_SENTENCE,
    blocked: blockedSentence(usage.renewsOn),
  }

  return sentences[usage.status]
}

export type AiUsagePageViewState = 'loading' | 'unavailable' | 'ready'

export function useAiUsagePage() {
  const { aiQuotaUsage, isLoadingAiQuotaUsage, refetchAiQuotaUsage } =
    useAiQuotaUsageQuery()

  const viewState: AiUsagePageViewState = isLoadingAiQuotaUsage
    ? 'loading'
    : aiQuotaUsage
      ? 'ready'
      : 'unavailable'
  const status: AiQuotaStatus | null = aiQuotaUsage?.status ?? null
  const percentage = aiQuotaUsage?.percentage ?? 0
  const renewalText = aiQuotaUsage
    ? `Renova em ${formatAiQuotaRenewalDate(aiQuotaUsage.renewsOn)}`
    : ''
  const statusSentence = aiQuotaUsage ? statusSentenceFor(aiQuotaUsage) : ''

  async function handleRetry() {
    await refetchAiQuotaUsage()
  }

  return {
    viewState,
    status,
    percentage,
    renewalText,
    statusSentence,
    handleRetry,
  }
}
