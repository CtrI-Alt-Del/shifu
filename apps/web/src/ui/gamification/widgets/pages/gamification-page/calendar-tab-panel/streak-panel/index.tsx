import type { PracticeStreak } from '@/core/gamification/practice-calendar'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type StreakPanelProps = {
  streak: PracticeStreak
  today: string
  isTodayPending: boolean
}

export const StreakPanel = ({ streak, today, isTodayPending }: StreakPanelProps) => {
  const { formatDayLabel } = useFormatDate()

  return (
    <section aria-labelledby='gamification-streak-title' className='space-y-6'>
      <h3 className='font-serif text-2xl' id='gamification-streak-title'>
        Sua constância
      </h3>

      <p className='flex items-center gap-3'>
        <span className='font-serif text-[64px] leading-none text-latao-text'>
          {streak.current}
        </span>
        <span className='text-muted-foreground'>
          {streak.current === 1 ? 'dia seguido' : 'dias seguidos'}
        </span>
      </p>

      <p className='flex items-center gap-2 text-sm text-muted-foreground'>
        <Icon className='text-latao-solid' name='trophy' size={18} />
        Maior sequência: {streak.longest} {streak.longest === 1 ? 'dia' : 'dias'}
      </p>

      <div className='space-y-3 rounded-[10px] bg-surface-alt p-6'>
        <p className='flex items-center gap-2 font-medium'>
          <Icon
            className='text-latao-text'
            name={isTodayPending ? 'clock-3' : 'circle-check'}
            size={18}
          />
          Hoje, {formatDayLabel(today)}
        </p>
        <p className='text-muted-foreground'>
          {isTodayPending
            ? 'Pratique hoje para manter sua sequência.'
            : 'Você já praticou hoje.'}
        </p>
        <p className='text-[13px] text-muted-foreground'>
          Um dia pode contar como prática mesmo sem ganho de XP.
        </p>
      </div>
    </section>
  )
}
