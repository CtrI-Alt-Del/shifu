import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type MonthNavigatorProps = {
  year: number
  month: number
  isAtCurrentMonth: boolean
  isAtEarliestMonth: boolean
  onPreviousMonth: () => void
  onNextMonth: () => void
}

export const MonthNavigator = ({
  year,
  month,
  isAtCurrentMonth,
  isAtEarliestMonth,
  onPreviousMonth,
  onNextMonth,
}: MonthNavigatorProps) => {
  const { formatMonthLabel } = useFormatDate()

  return (
    <div className='flex items-center justify-between'>
      <h3 className='font-serif text-2xl'>{formatMonthLabel(year, month)}</h3>
      <div className='flex items-center gap-2'>
        <button
          aria-label='Mês anterior'
          className='flex size-11 items-center justify-center rounded-[10px] border border-control-border bg-surface-alt disabled:border-transparent disabled:bg-transparent disabled:text-muted-foreground'
          disabled={isAtEarliestMonth}
          onClick={onPreviousMonth}
          type='button'
        >
          <Icon name='chevron-left' size={18} />
        </button>
        <button
          aria-label='Próximo mês'
          className='flex size-11 items-center justify-center rounded-[10px] border border-control-border bg-surface-alt disabled:border-transparent disabled:bg-transparent disabled:text-muted-foreground'
          disabled={isAtCurrentMonth}
          onClick={onNextMonth}
          type='button'
        >
          <Icon name='chevron-right' size={18} />
        </button>
      </div>
    </div>
  )
}
