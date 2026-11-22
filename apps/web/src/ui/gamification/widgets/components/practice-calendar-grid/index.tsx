import { motion } from 'motion/react'

import type { CalendarDay } from '@/core/gamification/practice-calendar'
import { ENTRANCE_FAST_STAGGER } from '@/constants/motion-variants'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'

import { CalendarDayCell } from './calendar-day-cell'

// Without `onSelectDay` the grid is display-only: day cells are not buttons and
// carry their date and state as visually hidden text instead.
export type PracticeCalendarGridProps = {
  days: CalendarDay[]
  selectedDay?: CalendarDay | null
  onSelectDay?: (day: CalendarDay) => void
  // Short 40 px cells drawn by fill and border only, for the panel's month card.
  // The week still opens on Monday, as in the Calendário tab.
  compact?: boolean
}

// The design opens the week on Monday; `getUTCDay` returns 0 for Sunday, so
// Sunday has to move to the end of the row rather than the start.
const WEEKDAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

export const PracticeCalendarGrid = ({
  days,
  selectedDay = null,
  onSelectDay,
  compact = false,
}: PracticeCalendarGridProps) => {
  const { formatWeekdayLabel } = useFormatDate()
  const leadingBlanks = days.length > 0 ? mondayFirstIndex(days[0].day) : 0

  return (
    <div className={compact ? 'space-y-1.5' : 'space-y-2'}>
      <div className={`grid grid-cols-7 ${compact ? 'gap-1.5' : 'gap-2 pb-2'}`}>
        {WEEKDAY_LABELS.map((label) => (
          <span className='text-center text-[13px] text-muted-foreground' key={label}>
            {label}
          </span>
        ))}
      </div>
      <motion.div
        className={`grid grid-cols-7 ${compact ? 'gap-1.5' : 'gap-2'}`}
        variants={ENTRANCE_FAST_STAGGER}
      >
        {Array.from({ length: leadingBlanks }, (_, index) => (
          <span
            aria-hidden='true'
            className={compact ? 'h-10' : 'h-16'}
            key={`blank-${days[0]?.day ?? 'empty'}-${index}`}
          />
        ))}
        {days.map((day) => (
          <CalendarDayCell
            compact={compact}
            day={day}
            isSelected={selectedDay?.day === day.day}
            key={day.day}
            label={formatWeekdayLabel(day.day)}
            onSelect={onSelectDay}
          />
        ))}
      </motion.div>
    </div>
  )
}

function mondayFirstIndex(isoDate: string): number {
  const weekday = new Date(`${isoDate}T00:00:00Z`).getUTCDay()
  return (weekday + 6) % 7
}
