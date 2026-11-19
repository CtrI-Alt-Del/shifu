import type { AiQuotaStatus } from '@/core/intelligence/ai-quota-usage'
import { useAiQuotaUsageQuery } from '@/ui/intelligence/hooks/use-ai-quota-usage-query'
import type { IconName } from '@/ui/shared/widgets/components/icon'

const MUTED_TONE_CLASS_NAME = 'text-muted-foreground'
const ALERT_TONE_CLASS_NAME = 'text-selo-text'

const STATUS_LABELS: Record<AiQuotaStatus, string> = {
  normal: '',
  near_limit: ', perto do limite',
  blocked: ', cota esgotada',
}

// Only the near-limit and blocked states carry an icon, as on the design board.
const STATUS_ICONS: Record<AiQuotaStatus, IconName | null> = {
  normal: null,
  near_limit: 'triangle-alert',
  blocked: 'circle-pause',
}

const STATUS_TONE_CLASS_NAMES: Record<AiQuotaStatus, string> = {
  normal: MUTED_TONE_CLASS_NAME,
  near_limit: ALERT_TONE_CLASS_NAME,
  blocked: ALERT_TONE_CLASS_NAME,
}

type AiQuotaIndicatorState = {
  isVisible: boolean
  text: string
  label: string
  iconName: IconName | null
  toneClassName: string
}

const HIDDEN_STATE: AiQuotaIndicatorState = {
  isVisible: false,
  text: '',
  label: '',
  iconName: null,
  toneClassName: MUTED_TONE_CLASS_NAME,
}

const UNAVAILABLE_STATE: AiQuotaIndicatorState = {
  isVisible: true,
  text: 'IA · indisponível',
  label: 'Uso da IA: indisponível no momento',
  iconName: null,
  toneClassName: MUTED_TONE_CLASS_NAME,
}

export function useAiQuotaIndicator(): AiQuotaIndicatorState {
  const { aiQuotaUsage, isLoadingAiQuotaUsage } = useAiQuotaUsageQuery()

  if (isLoadingAiQuotaUsage) return HIDDEN_STATE
  if (!aiQuotaUsage) return UNAVAILABLE_STATE

  return {
    isVisible: true,
    text: `IA · ${aiQuotaUsage.percentage}%`,
    label: `Uso da IA: ${aiQuotaUsage.percentage}% da cota mensal${STATUS_LABELS[aiQuotaUsage.status]}`,
    iconName: STATUS_ICONS[aiQuotaUsage.status],
    toneClassName: STATUS_TONE_CLASS_NAMES[aiQuotaUsage.status],
  }
}
