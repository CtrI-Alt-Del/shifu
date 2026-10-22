import type { StreakOverview } from '@/core/gamification/overview'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { PracticeWeekStrip } from './practice-week-strip'

export type StreakSummaryCardProps = {
  streak: StreakOverview
}

export const StreakSummaryCard = ({ streak }: StreakSummaryCardProps) => {
  const { formatDayLabel } = useFormatDate()

  return (
    <section
      aria-labelledby='gamification-overview-streak-title'
      className='space-y-6 rounded-[14px] border border-border bg-card p-6'
    >
      <h3 className='font-serif text-2xl' id='gamification-overview-streak-title'>
        Sua constância
      </h3>

      <p className='flex items-center gap-3'>
        <span className='font-serif text-[64px] leading-none text-latao-text'>
          {streak.streak.current}
        </span>
        <span className='text-muted-foreground'>
          {streak.streak.current === 1 ? 'dia seguido' : 'dias seguidos'}
        </span>
      </p>

      <p className='flex items-center gap-2 text-sm text-muted-foreground'>
        <Icon className='text-latao-solid' name='trophy' size={18} />
        Maior sequência: {streak.streak.longest}{' '}
        {streak.streak.longest === 1 ? 'dia' : 'dias'}
      </p>

      <PracticeWeekStrip days={streak.lastSevenDays} />

      <div className='space-y-2 rounded-[10px] bg-surface-alt p-6'>
        <p className='flex items-center gap-2 font-medium'>
          <Icon
            className='text-latao-text'
            name={streak.isTodayPending ? 'clock-3' : 'circle-check'}
            size={18}
          />
          Hoje, {formatDayLabel(streak.today)}
        </p>
        <p className='text-muted-foreground'>
          {streak.isTodayPending
            ? 'Pratique hoje para manter sua sequência.'
            : 'Você já praticou hoje.'}
        </p>
      </div>
    </section>
  )
}
