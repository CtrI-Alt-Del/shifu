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
