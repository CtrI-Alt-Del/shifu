import type { CalendarDay } from '@/core/gamification/practice-calendar'
import {
  CALENDAR_DAY_PRESENTATION,
  CALENDAR_DAY_STATE_LABEL,
} from '@/ui/gamification/constants/calendar-day-presentation'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'

export type PracticeWeekStripProps = {
  days: CalendarDay[]
}

const WEEKDAY_INITIALS = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S']

export const PracticeWeekStrip = ({ days }: PracticeWeekStripProps) => {
  const { formatDayLabel } = useFormatDate()

  return (
    <ul aria-label='Últimos sete dias' className='flex justify-between gap-1'>
      {days.map((day) => {
        const presentation = CALENDAR_DAY_PRESENTATION[day.state]
        const weekday = new Date(`${day.day}T00:00:00Z`).getUTCDay()

        return (
          <li
            aria-label={`${formatDayLabel(day.day)}, ${CALENDAR_DAY_STATE_LABEL[day.state]}`}
            className={`flex h-14 flex-1 flex-col items-center justify-center gap-1.5 rounded-[10px] ${presentation.surface}`}
            key={day.day}
          >
            <span aria-hidden='true' className='font-mono text-xs text-muted-foreground'>
              {WEEKDAY_INITIALS[weekday]}
            </span>
            {presentation.icon ? (
              <Icon
                className={presentation.iconClassName}
                name={presentation.icon}
                size={14}
              />
            ) : (
              <span
                aria-hidden='true'
                className='size-1 rounded-full bg-muted-foreground'
              />
            )}
          </li>
        )
      })}
    </ul>
  )
}
