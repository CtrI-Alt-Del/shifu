import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useAiQuotaWarningCard } from './use-ai-quota-warning-card'

export type AiQuotaWarningCardProps = {
  accountId: string
  /** Current usage, whole percent, shown in the warning message. */
  percentage: number
  /** ISO 8601 date of the next renewal; the month before it keys the dismissal. */
  renewsOn: string
  className?: string
}

export const AiQuotaWarningCard = (props: AiQuotaWarningCardProps) => {
  const { isDismissed, message, handleDismiss } = useAiQuotaWarningCard(props)

  if (isDismissed) return null

  return (
    <output
      className={`flex items-start gap-3 rounded-xl border border-primary/45! bg-accent p-[3px] pl-[15px] text-selo-text ${props.className ?? ''}`}
    >
      <Icon className='mt-2 shrink-0' name='triangle-alert' size={18} />
      <p className='min-w-0 flex-1 py-3 text-sm leading-normal'>{message}</p>
      <Button
        aria-label='Dispensar aviso'
        className='size-11 shrink-0 p-0! text-secondary-foreground!'
        onClick={handleDismiss}
        type='button'
        variant='ghost'
      >
        <Icon name='x' size={16} />
      </Button>
    </output>
  )
}
