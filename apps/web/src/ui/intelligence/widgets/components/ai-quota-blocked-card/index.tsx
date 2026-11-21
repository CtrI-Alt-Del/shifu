import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type AiQuotaBlockedCardProps = {
  /** Target of `aria-describedby` on every control that the quota blocked. */
  id: string
  message: string
  /** `alert` only right after a refusal, so the change is announced once. */
  role?: 'status' | 'alert'
  className?: string
}

/**
 * The 1 px border counts inside the board sizes, so the padding is 1 px smaller than the
 * board's. `border-primary/45!` is important because the global `* { border-color }` rule is
 * unlayered and would otherwise beat every border color utility.
 * Inline when the container is wide (message and link on one row, 52 px), stacked
 * when it is narrow (link under the message, aligned with the message text).
 */
export const AiQuotaBlockedCard = ({
  id,
  message,
  role = 'status',
  className = '',
}: AiQuotaBlockedCardProps) => {
  return (
    <div className={`@container ${className}`}>
      <div
        className='flex flex-wrap items-start gap-x-3 gap-y-1 rounded-xl border border-primary/45! bg-accent pt-[11px] pr-[11px] pb-1 pl-[15px] text-selo-text @xl:flex-nowrap @xl:items-center @xl:pt-[3px] @xl:pr-[3px] @xl:pb-[3px]'
        id={id}
        role={role}
      >
        <Icon className='shrink-0' name='circle-pause' size={16} />
        <p className='min-w-0 flex-1 basis-[calc(100%-28px)] text-sm leading-[1.2] @xl:basis-0'>
          {message}
        </p>
        <Anchor
          className='ml-5 inline-flex min-h-11 shrink-0 items-center px-2 text-sm font-medium text-foreground underline underline-offset-4 @xl:ml-0'
          route='accountAiUsage'
        >
          Ver uso da IA
        </Anchor>
      </div>
    </div>
  )
}
