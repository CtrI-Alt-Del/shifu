import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'

import type { IndicatorView } from '../use-skill-completion'

export type SkillCompletionIndicatorsProps = {
  indicators: IndicatorView[]
}

export const SkillCompletionIndicators = ({
  indicators,
}: SkillCompletionIndicatorsProps) => {
  return (
    <motion.ul
      aria-label='Indicadores da Habilidade'
      className='flex flex-col rounded-xl border border-border bg-surface-alt p-2 lg:flex-row lg:gap-4 lg:border-0 lg:bg-transparent lg:p-0'
      variants={ENTRANCE_SECTION}
    >
      {indicators.map((indicator) => (
        <li
          className='flex items-center justify-between gap-3 px-4 py-3 not-first:border-t not-first:border-border lg:w-[calc((100%-2rem)/3)] lg:flex-none lg:flex-col-reverse lg:items-start lg:justify-end lg:gap-1 lg:rounded-xl lg:border lg:border-border lg:bg-surface-alt lg:px-5 lg:py-4'
          key={indicator.id}
        >
          <span className='text-sm leading-[1.2] text-secondary-foreground lg:text-[13px] lg:text-muted-foreground'>
            {indicator.label}
          </span>
          <strong className='font-mono text-base font-semibold leading-[1.2] text-foreground lg:text-xl'>
            <AnimatedNumber
              delay={0.3}
              format={indicator.format}
              value={indicator.value}
            />
          </strong>
        </li>
      ))}
    </motion.ul>
  )
}
