import type { CalendarDay, CalendarDayState } from '@/core/gamification/practice-calendar'
import type { IconName } from '@/ui/shared/widgets/components/icon'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'

export type PracticeWeekStripProps = {
  days: CalendarDay[]
}

// Mirrors the Calendário tab's day-cell vocabulary: every state carries its
// own surface and glyph, never colour alone (RP-13).
const STATE_PRESENTATION: Record<
  CalendarDayState,
  { surface: string; icon: IconName | null; iconClassName: string }
> = {
  neutral: { surface: '', icon: null, iconClassName: '' },
  practiced: {
    surface: '',
    icon: 'check',
    iconClassName: 'rounded-full border border-latao-solid! p-[3px] text-latao-text',
  },
  'current-streak': {
    surface: 'bg-latao-tint',
    icon: 'check',
    iconClassName: 'text-latao-solid',
  },
  missed: { surface: '', icon: 'minus', iconClassName: 'text-muted-foreground' },
  'today-pending': {
    surface: 'border border-latao-solid!',
    icon: 'clock-3',
    iconClassName: 'text-latao-solid',
  },
}

const STATE_LABEL: Record<CalendarDayState, string> = {
  neutral: 'sem registro',
  practiced: 'dia de prática',
  'current-streak': 'dia da sequência atual',
  missed: 'dia encerrado sem prática',
  'today-pending': 'hoje, prática ainda pendente',
}

const WEEKDAY_INITIALS = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S']

export const PracticeWeekStrip = ({ days }: PracticeWeekStripProps) => {
  const { formatDayLabel } = useFormatDate()

  return (
    <ul aria-label='Últimos sete dias' className='flex justify-between gap-1'>
      {days.map((day) => {
        const presentation = STATE_PRESENTATION[day.state]
        const weekday = new Date(`${day.day}T00:00:00Z`).getUTCDay()

        return (
          <li
            aria-label={`${formatDayLabel(day.day)}, ${STATE_LABEL[day.state]}`}
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
