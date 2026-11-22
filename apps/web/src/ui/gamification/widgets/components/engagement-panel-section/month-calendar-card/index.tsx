import { motion } from 'motion/react'

import { ENTRANCE_CARD } from '@/constants/motion-variants'
import type { CalendarDay } from '@/core/gamification/practice-calendar'
import { CalendarLegend } from '@/ui/gamification/widgets/components/calendar-legend'
import { PracticeCalendarGrid } from '@/ui/gamification/widgets/components/practice-calendar-grid'
import { Anchor } from '@/ui/shared/widgets/components/anchor'

export type MonthCalendarCardProps = {
  monthLabel: string
  days: CalendarDay[]
}

// The month is display-only: day selection stays in the Calendário tab, so the
// grid receives no handler and its days are text, not buttons.
export const MonthCalendarCard = ({ monthLabel, days }: MonthCalendarCardProps) => (
  <motion.article
    aria-labelledby='engagement-month-calendar-title'
    className='space-y-4 rounded-[14px] border border-border bg-surface-alt p-5'
    variants={ENTRANCE_CARD}
  >
    <div className='flex flex-wrap items-center justify-between gap-x-3'>
      <h3 className='font-semibold' id='engagement-month-calendar-title'>
        {monthLabel}
      </h3>
      <Anchor
        className='inline-flex min-h-11 items-center text-sm font-medium text-secondary-foreground underline underline-offset-2 hover:text-foreground lg:min-h-0'
        route='gamificationCalendar'
      >
        Abrir calendário
      </Anchor>
    </div>
    <PracticeCalendarGrid compact days={days} />
    <CalendarLegend compact />
  </motion.article>
)
