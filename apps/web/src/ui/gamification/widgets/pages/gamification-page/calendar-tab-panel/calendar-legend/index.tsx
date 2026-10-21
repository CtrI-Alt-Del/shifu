import { Icon } from '@/ui/shared/widgets/components/icon'

const LEGEND_ENTRIES = [
  {
    label: 'Neutro',
    description: 'Antes da primeira prática ou em dias futuros.',
    mark: null,
    markClassName: '',
  },
  {
    label: 'Dia de prática',
    description: 'Houve prática fora da sequência atual.',
    mark: 'check',
    markClassName: 'rounded-full border border-latao-solid! p-[3px] text-latao-text',
  },
  {
    label: 'Sequência atual',
    description: 'Dia que faz parte da sequência ativa.',
    mark: 'check',
    markClassName: 'rounded-[10px] bg-latao-tint p-[3px] text-latao-solid',
  },
  {
    label: 'Sem prática',
    description: 'Dia encerrado sem registro de prática.',
    mark: 'minus',
    markClassName: 'text-muted-foreground',
  },
  {
    label: 'Hoje pendente',
    description: 'O dia ainda pode contar para a sequência.',
    mark: 'clock-3',
    markClassName: 'rounded-[10px] border border-latao-solid! p-[3px] text-latao-solid',
  },
] as const

export const CalendarLegend = () => {
  return (
    <section
      aria-labelledby='gamification-legend-title'
      className='space-y-4 border-t border-border pt-6'
    >
      <h3 className='font-medium' id='gamification-legend-title'>
        Estados dos dias
      </h3>
      <ul className='grid gap-6 sm:grid-cols-2 lg:grid-cols-5'>
        {LEGEND_ENTRIES.map((entry) => (
          <li className='flex items-start gap-3' key={entry.label}>
            <span className='flex size-9 shrink-0 items-center justify-center'>
              {entry.mark ? (
                <Icon className={entry.markClassName} name={entry.mark} size={16} />
              ) : (
                <span
                  aria-hidden='true'
                  className='size-1 rounded-full bg-muted-foreground'
                />
              )}
            </span>
            <span className='space-y-1'>
              <span className='block text-[13px] font-medium'>{entry.label}</span>
              <span className='block text-xs text-muted-foreground'>
                {entry.description}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
