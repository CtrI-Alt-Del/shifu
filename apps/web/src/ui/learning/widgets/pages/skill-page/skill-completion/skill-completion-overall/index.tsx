import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'

import { SkillCompletionComparisonBar } from '../skill-completion-comparison-bar'
import { SkillCompletionScoreChange } from '../skill-completion-score-change'
import type { OverallView } from '../use-skill-completion'

export type SkillCompletionOverallProps = {
  overall: OverallView
}

export const SkillCompletionOverall = ({ overall }: SkillCompletionOverallProps) => {
  return (
    <motion.section
      aria-labelledby='skill-completion-overall-title'
      className='rounded-xl border border-border bg-surface-alt p-2'
      variants={ENTRANCE_SECTION}
    >
      <div className='flex flex-col gap-2.5 p-4 lg:flex-row lg:items-center lg:gap-4 lg:py-5'>
        <div className='flex items-center gap-3 lg:contents'>
          <div className='flex min-w-0 flex-1 flex-col gap-0.5 lg:order-1 lg:w-[280px] lg:flex-none'>
            <h2
              className='text-base font-semibold leading-[1.2] text-foreground lg:leading-6'
              id='skill-completion-overall-title'
            >
              {overall.label}
            </h2>
            {overall.startingLabel ? (
              <p className='text-[13px] leading-4 text-muted-foreground lg:leading-5'>
                {overall.startingLabel}
              </p>
            ) : null}
          </div>
          <SkillCompletionScoreChange className='lg:order-3' comparison={overall} />
          <span aria-hidden='true' className='size-4 shrink-0 lg:order-4' />
        </div>
        <SkillCompletionComparisonBar
          className='lg:order-2 lg:flex-1'
          gainPercent={overall.gainPercent}
          startingPercent={overall.startingPercent}
          unknownPercent={overall.unknownPercent}
        />
      </div>
    </motion.section>
  )
}
