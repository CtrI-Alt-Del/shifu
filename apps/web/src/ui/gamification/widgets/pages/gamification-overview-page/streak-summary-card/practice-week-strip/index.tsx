import { motion } from 'motion/react'

import type { CalendarDay } from '@/core/gamification/practice-calendar'
import {
  CALENDAR_DAY_PRESENTATION,
  CALENDAR_DAY_STATE_LABEL,
} from '@/ui/gamification/constants/calendar-day-presentation'
import { ENTRANCE_STAGGER, ENTRANCE_POP } from '@/constants/motion-variants'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type PracticeWeekStripProps = {
  days: CalendarDay[]
  today: string
}

const WEEKDAY_LABELS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

export const PracticeWeekStrip = ({ days, today }: PracticeWeekStripProps) => {
  const { formatDayLabel } = useFormatDate()

  return (
    <motion.ul
      aria-label='Últimos sete dias'
      className='flex justify-between gap-1'
      variants={ENTRANCE_STAGGER}
    >
      {days.map((day) => {
        const presentation = CALENDAR_DAY_PRESENTATION[day.state]
        const date = new Date(`${day.day}T00:00:00Z`)
        const isToday = day.day === today

        return (
          <motion.li
            aria-label={`${formatDayLabel(day.day)}, ${CALENDAR_DAY_STATE_LABEL[day.state]}`}
            className='flex w-[42px] flex-col items-center gap-2'
            key={day.day}
            variants={ENTRANCE_POP}
          >
            <span
              aria-hidden='true'
              className={`text-xs ${isToday ? 'text-foreground' : 'text-muted-foreground'}`}
            >
              {isToday ? 'Hoje' : WEEKDAY_LABELS[date.getUTCDay()]}
            </span>
            <span
              aria-hidden='true'
              className={`grid h-9 w-10 place-items-center rounded-[6px] ${presentation.surface}`}
            >
              {presentation.icon ? (
                <Icon
                  className={presentation.iconClassName}
                  name={presentation.icon}
                  size={14}
                />
              ) : (
                <span className='size-1 rounded-full bg-muted-foreground' />
              )}
            </span>
            <span
              aria-hidden='true'
              className='font-mono text-xs text-secondary-foreground'
            >
              {date.getUTCDate()}
            </span>
          </motion.li>
        )
      })}
    </motion.ul>
  )
}
