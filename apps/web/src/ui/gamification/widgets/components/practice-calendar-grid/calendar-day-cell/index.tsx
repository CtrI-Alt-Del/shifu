import { motion } from 'motion/react'

import type { CalendarDay } from '@/core/gamification/practice-calendar'
import {
  CALENDAR_DAY_PRESENTATION,
  CALENDAR_DAY_STATE_LABEL,
  COMPACT_CALENDAR_DAY_PRESENTATION,
} from '@/ui/gamification/constants/calendar-day-presentation'
import { ENTRANCE_POP } from '@/constants/motion-variants'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type CalendarDayCellProps = {
  day: CalendarDay
  label: string
  isSelected: boolean
  compact?: boolean
  onSelect?: (day: CalendarDay) => void
}

export const CalendarDayCell = ({
  day,
  label,
  isSelected,
  compact = false,
  onSelect,
}: CalendarDayCellProps) => {
  const presentation = CALENDAR_DAY_PRESENTATION[day.state]
  const dayNumber = Number(day.day.slice(8, 10))
  const className = compact
    ? `flex h-10 items-center justify-center rounded-md ${COMPACT_CALENDAR_DAY_PRESENTATION[day.state]}`
    : `flex h-16 flex-col items-center justify-center gap-2 rounded-[12px] ${presentation.surface} ${isSelected ? 'ring-1 ring-latao-solid' : ''}`
  const content = compact ? (
    <span className='font-mono text-sm'>{dayNumber}</span>
  ) : (
    <>
      <span className={`font-mono text-sm ${presentation.number}`}>{dayNumber}</span>
      {presentation.icon ? (
        <Icon className={presentation.iconClassName} name={presentation.icon} size={14} />
      ) : (
        <span aria-hidden='true' className='size-1 rounded-full bg-muted-foreground' />
      )}
    </>
  )

  if (!onSelect) {
    return (
      <motion.div className={className} variants={ENTRANCE_POP}>
        {content}
        <span className='sr-only'>{`${label}, ${CALENDAR_DAY_STATE_LABEL[day.state]}`}</span>
      </motion.div>
    )
  }

  return (
    <motion.button
      aria-current={isSelected ? 'date' : undefined}
      aria-label={`${label}, ${CALENDAR_DAY_STATE_LABEL[day.state]}`}
      className={className}
      onClick={() => onSelect(day)}
      type='button'
      variants={ENTRANCE_POP}
      whileTap={{ scale: 0.94 }}
    >
      {content}
    </motion.button>
  )
}
