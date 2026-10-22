import type { XpHistoryEntry, XpSource } from '@/core/gamification/xp-history'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import type { IconName } from '@/ui/shared/widgets/components/icon'
import { Icon } from '@/ui/shared/widgets/components/icon'

const ICON_BY_SOURCE: Record<XpSource, IconName> = {
  activity: 'target',
  diagnosis: 'clipboard-check',
  'competency-mastery': 'badge-check',
  'skill-completion': 'graduation-cap',
  achievement: 'award',
}

type XpHistoryRowProps = {
  entry: XpHistoryEntry
}

export const XpHistoryRow = ({ entry }: XpHistoryRowProps) => {
  const { formatShortDate } = useFormatDate()
  const grantedLabel = formatShortDate(entry.grantedAt)
  const occurredLabel = formatShortDate(entry.occurredAt)
  const amountLabel = `+${entry.amount.toLocaleString('pt-BR')} XP`

  return (
    <li className='border-b border-border last:border-b-0'>
      {/* The row renders no link and no action: T34 gives the history no
          navigation shortcut to the origin, removed or not. Its own text
          carries the origin, the kind, the date and the amount, so nothing
          here depends on the mark or on colour. */}
      <div className='flex flex-col gap-4 px-6 py-5 sm:flex-row sm:items-center sm:gap-6'>
        <div
          aria-hidden='true'
          className='flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-latao-tint'
        >
          <Icon
            className='text-latao-text'
            name={ICON_BY_SOURCE[entry.source]}
            size={18}
          />
        </div>

        <div className='flex-1 space-y-1'>
          <p className='text-[15px]'>{entry.title}</p>
          <p className='text-[13px] text-muted-foreground'>{entry.detail}</p>
        </div>

        <div className='space-y-1 sm:w-[164px]'>
          <p className='text-sm'>{grantedLabel}</p>
          {occurredLabel === grantedLabel ? null : (
            <p className='text-xs text-muted-foreground'>Fato em {occurredLabel}</p>
          )}
        </div>

        <p className='text-[17px] text-latao-text sm:text-right'>{amountLabel}</p>
      </div>
    </li>
  )
}
