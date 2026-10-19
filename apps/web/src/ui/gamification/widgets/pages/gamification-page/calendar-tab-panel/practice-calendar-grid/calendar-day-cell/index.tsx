import type { CalendarDay, CalendarDayState } from '@/core/gamification/practice-calendar'
import type { IconName } from '@/ui/shared/widgets/components/icon'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type CalendarDayCellProps = {
  day: CalendarDay
  label: string
  isSelected: boolean
  onSelect: (day: CalendarDay) => void
}

// Every state carries its own shape and glyph, never colour alone, so the
// calendar stays readable without colour perception (RP-13).
const STATE_PRESENTATION: Record<
  CalendarDayState,
  { surface: string; number: string; icon: IconName | null; iconClassName: string }
> = {
  neutral: {
    surface: '',
    number: 'text-muted-foreground',
    icon: null,
    iconClassName: '',
  },
  practiced: {
    surface: '',
    number: 'text-foreground',
    icon: 'check',
    iconClassName: 'rounded-full border border-latao-solid! p-[3px] text-latao-text',
  },
  'current-streak': {
    surface: 'bg-latao-tint',
    number: 'text-latao-text',
    icon: 'check',
    iconClassName: 'text-latao-solid',
  },
  missed: {
    surface: '',
    number: 'text-foreground',
    icon: 'minus',
    iconClassName: 'text-muted-foreground',
  },
  'today-pending': {
    surface: 'border border-latao-solid!',
    number: 'text-latao-text',
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

export const CalendarDayCell = ({
  day,
  label,
  isSelected,
  onSelect,
}: CalendarDayCellProps) => {
  const presentation = STATE_PRESENTATION[day.state]
  const dayNumber = Number(day.day.slice(8, 10))

  return (
    <button
      aria-current={isSelected ? 'date' : undefined}
      aria-label={`${label}, ${STATE_LABEL[day.state]}`}
      className={`flex h-16 flex-col items-center justify-center gap-2 rounded-[10px] ${presentation.surface} ${isSelected ? 'ring-1 ring-latao-solid' : ''}`}
      onClick={() => onSelect(day)}
      type='button'
    >
      <span className={`font-mono text-sm ${presentation.number}`}>{dayNumber}</span>
      {presentation.icon ? (
        <Icon className={presentation.iconClassName} name={presentation.icon} size={14} />
      ) : (
        <span aria-hidden='true' className='size-1 rounded-full bg-muted-foreground' />
      )}
    </button>
  )
}
