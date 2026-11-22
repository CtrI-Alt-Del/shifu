import { motion } from 'motion/react'

import { ENTRANCE_RISE } from '@/constants/motion-variants'

import type { LegendItemView, LegendTone } from '../use-skill-completion'

export type SkillCompletionLegendProps = {
  items: LegendItemView[]
}

const SWATCH_CLASS_NAMES: Record<LegendTone, string> = {
  start: 'bg-jade-fill',
  evolution: 'bg-jade-text',
  unknown: 'bg-muted-foreground',
}

export const SkillCompletionLegend = ({ items }: SkillCompletionLegendProps) => {
  return (
    <motion.ul
      aria-label='Legenda da comparação'
      className='flex flex-wrap items-center gap-x-4 gap-y-2'
      variants={ENTRANCE_RISE}
    >
      {items.map((item) => (
        <li
          className='flex items-center gap-2 text-xs leading-[1.2] text-muted-foreground'
          key={item.id}
        >
          <span
            aria-hidden='true'
            className={`h-2 w-3 shrink-0 rounded-full ${SWATCH_CLASS_NAMES[item.tone]}`}
          />
          {item.label}
        </li>
      ))}
    </motion.ul>
  )
}
