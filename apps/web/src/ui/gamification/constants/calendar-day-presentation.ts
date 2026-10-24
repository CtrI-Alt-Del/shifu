import type { CalendarDayState } from '@/core/gamification/practice-calendar'
import type { IconName } from '@/ui/shared/widgets/components/icon'

// Shared by the Calendário grid and the Visão geral week strip: every state
// carries its own shape and glyph, never colour alone, and both tabs must
// classify a day identically (RP-13).
export const CALENDAR_DAY_PRESENTATION: Record<
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

export const CALENDAR_DAY_STATE_LABEL: Record<CalendarDayState, string> = {
  neutral: 'sem registro',
  practiced: 'dia de prática',
  'current-streak': 'dia da sequência atual',
  missed: 'dia encerrado sem prática',
  'today-pending': 'hoje, prática ainda pendente',
}
