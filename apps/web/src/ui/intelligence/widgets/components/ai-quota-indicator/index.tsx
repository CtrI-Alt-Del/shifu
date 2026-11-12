import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useAiQuotaIndicator } from './use-ai-quota-indicator'

export const AiQuotaIndicator = () => {
  const { isVisible, text, label, iconName, toneClassName } = useAiQuotaIndicator()

  if (!isVisible) return null

  return (
    <Anchor
      aria-label={label}
      className={`inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-md px-2 font-mono text-xs transition-colors hover:text-foreground ${toneClassName}`}
      route='accountAiUsage'
    >
      {iconName ? <Icon name={iconName} size={14} /> : null}
      <span>{text}</span>
    </Anchor>
  )
}
