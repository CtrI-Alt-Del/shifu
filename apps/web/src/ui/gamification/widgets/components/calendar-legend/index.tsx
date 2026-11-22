import { motion } from 'motion/react'

import {
  ENTRANCE_POP,
  ENTRANCE_SECTION,
  ENTRANCE_STAGGER,
} from '@/constants/motion-variants'
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
    markClassName: 'rounded-[12px] bg-latao-tint p-[3px] text-latao-solid',
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
    markClassName: 'rounded-[12px] border border-latao-solid! p-[3px] text-latao-solid',
  },
] as const

// The panel's month card draws its cells by fill and border (see
// `COMPACT_CALENDAR_DAY_PRESENTATION`), so its legend uses the matching swatches. Neutral
// days carry no mark and need no entry.
const COMPACT_LEGEND_ENTRIES = [
  {
    label: 'Sequência atual',
    description: 'Dia que faz parte da sequência ativa.',
    swatchClassName: 'bg-latao-fill',
  },
  {
    label: 'Dia de prática',
    description: 'Houve prática fora da sequência atual.',
    swatchClassName: 'border border-latao-solid/50! bg-latao-tint',
  },
  {
    label: 'Hoje, ainda dá para praticar',
    description: 'O dia ainda pode contar para a sequência.',
    swatchClassName: 'border border-dashed border-latao-solid!',
  },
  {
    label: 'Sem prática',
    description: 'Dia encerrado sem registro de prática.',
    swatchClassName: 'border border-control-border!',
  },
] as const

export type CalendarLegendProps = {
  // Label-only legend for narrow containers such as the panel's month card;
  // each state's description stays available to screen readers.
  compact?: boolean
}

export const CalendarLegend = ({ compact = false }: CalendarLegendProps) => {
  if (compact) {
    return (
      <motion.section
        aria-labelledby='gamification-legend-title'
        variants={ENTRANCE_SECTION}
      >
        <h3 className='sr-only' id='gamification-legend-title'>
          Estados dos dias
        </h3>
        <motion.ul className='flex flex-wrap gap-x-4 gap-y-2' variants={ENTRANCE_STAGGER}>
          {COMPACT_LEGEND_ENTRIES.map((entry) => (
            <motion.li
              className='flex items-center gap-2'
              key={entry.label}
              variants={ENTRANCE_POP}
            >
              <span
                aria-hidden='true'
                className={`size-4 shrink-0 rounded-[4px] ${entry.swatchClassName}`}
              />
              <span className='text-[13px] text-secondary-foreground'>{entry.label}</span>
              <span className='sr-only'>. {entry.description}</span>
            </motion.li>
          ))}
        </motion.ul>
      </motion.section>
    )
  }

  return (
    <motion.section
      aria-labelledby='gamification-legend-title'
      className='space-y-4 border-t border-border pt-6'
      variants={ENTRANCE_SECTION}
    >
      <h3 className='font-medium' id='gamification-legend-title'>
        Estados dos dias
      </h3>
      <motion.ul
        className='grid gap-6 sm:grid-cols-2 lg:grid-cols-5'
        variants={ENTRANCE_STAGGER}
      >
        {LEGEND_ENTRIES.map((entry) => (
          <motion.li
            className='flex items-start gap-3'
            key={entry.label}
            variants={ENTRANCE_POP}
          >
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
          </motion.li>
        ))}
      </motion.ul>
    </motion.section>
  )
}
