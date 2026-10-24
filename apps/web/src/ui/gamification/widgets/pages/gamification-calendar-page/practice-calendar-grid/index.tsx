import { motion } from 'motion/react'

import type { CalendarDay } from '@/core/gamification/practice-calendar'
import { ENTRANCE_FAST_STAGGER } from '@/constants/motion-variants'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'

import { CalendarDayCell } from './calendar-day-cell'

export type PracticeCalendarGridProps = {
  days: CalendarDay[]
  selectedDay: CalendarDay | null
  onSelectDay: (day: CalendarDay) => void
}

// The design opens the week on Monday; `getUTCDay` returns 0 for Sunday, so
// Sunday has to move to the end of the row rather than the start.
const WEEKDAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

export const PracticeCalendarGrid = ({
  days,
  selectedDay,
  onSelectDay,
}: PracticeCalendarGridProps) => {
  const { formatWeekdayLabel } = useFormatDate()
  const leadingBlanks = days.length > 0 ? mondayFirstIndex(days[0].day) : 0

  return (
    <div className='space-y-2'>
      <div className='grid grid-cols-7 gap-2 pb-2'>
        {WEEKDAY_LABELS.map((label) => (
          <span className='text-center text-[13px] text-muted-foreground' key={label}>
            {label}
          </span>
        ))}
      </div>
      <motion.div className='grid grid-cols-7 gap-2' variants={ENTRANCE_FAST_STAGGER}>
        {Array.from({ length: leadingBlanks }, (_, index) => (
          <span
            aria-hidden='true'
            className='h-16'
            key={`blank-${days[0]?.day ?? 'empty'}-${index}`}
          />
        ))}
        {days.map((day) => (
          <CalendarDayCell
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
