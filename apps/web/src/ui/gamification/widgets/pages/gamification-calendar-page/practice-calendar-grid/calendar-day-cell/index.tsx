import { motion } from 'motion/react'

import type { CalendarDay } from '@/core/gamification/practice-calendar'
import {
  CALENDAR_DAY_PRESENTATION,
  CALENDAR_DAY_STATE_LABEL,
} from '@/ui/gamification/constants/calendar-day-presentation'
import { ENTRANCE_POP } from '@/constants/motion-variants'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type CalendarDayCellProps = {
  day: CalendarDay
  label: string
  isSelected: boolean
  onSelect: (day: CalendarDay) => void
}

export const CalendarDayCell = ({
  day,
  label,
  isSelected,
  onSelect,
}: CalendarDayCellProps) => {
  const presentation = CALENDAR_DAY_PRESENTATION[day.state]
  const dayNumber = Number(day.day.slice(8, 10))

  return (
    <motion.button
      aria-current={isSelected ? 'date' : undefined}
      aria-label={`${label}, ${CALENDAR_DAY_STATE_LABEL[day.state]}`}
      className={`flex h-16 flex-col items-center justify-center gap-2 rounded-[10px] ${presentation.surface} ${isSelected ? 'ring-1 ring-latao-solid' : ''}`}
      onClick={() => onSelect(day)}
      type='button'
      variants={ENTRANCE_POP}
      whileTap={{ scale: 0.94 }}
    >
      <span className={`font-mono text-sm ${presentation.number}`}>{dayNumber}</span>
      {presentation.icon ? (
        <Icon className={presentation.iconClassName} name={presentation.icon} size={14} />
      ) : (
        <span aria-hidden='true' className='size-1 rounded-full bg-muted-foreground' />
      )}
    </motion.button>
  )
}
