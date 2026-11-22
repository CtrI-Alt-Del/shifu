import { Link } from '@tanstack/react-router'
import { motion } from 'motion/react'

import { ENTRANCE_ROW } from '@/constants/motion-variants'
import { ROUTES } from '@/constants/routes'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { SkillCompletionComparisonBar } from '../../skill-completion-comparison-bar'
import { SkillCompletionScoreChange } from '../../skill-completion-score-change'
import type { CompetencyRowView } from '../../use-skill-completion'

export type SkillCompletionCompetencyRowProps = {
  competency: CompetencyRowView
}

export const SkillCompletionCompetencyRow = ({
  competency,
}: SkillCompletionCompetencyRowProps) => {
  return (
    <motion.li
      className='not-first:border-t not-first:border-border'
      variants={ENTRANCE_ROW}
    >
      <Link
        aria-label={competency.accessibleName}
        className='flex flex-col gap-2.5 rounded-lg p-4 transition-colors hover:bg-muted/60 lg:flex-row lg:items-center lg:gap-4 lg:py-5'
        params={competency.params}
        to={ROUTES.learningCompetency}
      >
        <span className='flex items-center gap-3 lg:contents'>
          <span className='flex min-w-0 flex-1 flex-col gap-0.5 lg:order-1 lg:w-[280px] lg:flex-none'>
            <span className='text-base font-medium leading-[1.2] text-foreground lg:leading-6'>
              {competency.competencyName}
            </span>
            {competency.startingLabel ? (
              <span className='text-[13px] leading-4 text-muted-foreground lg:leading-5'>
                {competency.startingLabel}
              </span>
            ) : null}
            <span className='text-[13px] leading-4 text-muted-foreground lg:leading-5'>
              {competency.masteryText}
            </span>
          </span>
          <SkillCompletionScoreChange className='lg:order-3' comparison={competency} />
          <Icon
            className='shrink-0 text-muted-foreground lg:order-4'
            name='chevron-right'
            size={16}
          />
        </span>
        <SkillCompletionComparisonBar
          className='lg:order-2 lg:flex-1'
          gainPercent={competency.gainPercent}
          startingPercent={competency.startingPercent}
          unknownPercent={competency.unknownPercent}
        />
      </Link>
    </motion.li>
  )
}
