import type { CalendarDay } from '@/core/gamification/practice-calendar'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SelectedDayConfirmationProps = {
  selectedDay: CalendarDay | null
}

// RP-06 allows confirming only *that* a day had practice — never how much XP
// it produced or how many Activities it contained.
export const SelectedDayConfirmation = ({
  selectedDay,
}: SelectedDayConfirmationProps) => {
  const { formatDayLabel } = useFormatDate()

  if (!selectedDay) {
    return (
      <p className='border-t border-border pt-4 text-sm text-muted-foreground'>
        Selecione um dia de prática para confirmar a data.
      </p>
    )
  }

  const hadPractice =
    selectedDay.state === 'practiced' || selectedDay.state === 'current-streak'

  return (
    <p
      aria-live='polite'
      className='flex items-center gap-2 border-t border-border pt-4 text-sm text-muted-foreground'
    >
      <Icon
        className={hadPractice ? 'text-latao-solid' : 'text-muted-foreground'}
        name={hadPractice ? 'circle-check' : 'minus'}
        size={18}
      />
      {formatDayLabel(selectedDay.day)} ·{' '}
      {hadPractice ? 'Houve prática neste dia' : 'Sem registro de prática'}
    </p>
  )
}
