import { Link } from '@tanstack/react-router'
import { motion } from 'motion/react'

import type { SkillCompletionOverview } from '@/core/learning/skill-experience'
import { ENTRANCE_RISE } from '@/constants/motion-variants'
import { ROUTES } from '@/constants/routes'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { SkillCompletionCompetencyList } from './skill-completion-competency-list'
import { SkillCompletionHeader } from './skill-completion-header'
import { SkillCompletionIndicators } from './skill-completion-indicators'
import { SkillCompletionLegend } from './skill-completion-legend'
import { SkillCompletionOverall } from './skill-completion-overall'
import { SkillReviewPractice } from './skill-review-practice'
import { useSkillCompletion } from './use-skill-completion'

export type SkillCompletionProps = {
  goalId: string
  skillId: string
  skillName: string
  completion: SkillCompletionOverview
  onRemove: (trigger: HTMLButtonElement) => void
}

export const SkillCompletion = (props: SkillCompletionProps) => {
  const {
    skillName,
    statusLabel,
    dateRange,
    dateRangeLabel,
    intro,
    indicators,
    legendItems,
    overall,
    competencies,
    review,
    goalParams,
  } = useSkillCompletion(props)

  return (
    <div className='mx-auto w-full max-w-7xl'>
      <MotionEntrance className='mx-auto flex w-full max-w-[1150px] flex-col gap-6'>
        <SkillCompletionHeader
          dateRange={dateRange}
          dateRangeLabel={dateRangeLabel}
          onRemove={props.onRemove}
          skillName={skillName}
          statusLabel={statusLabel}
        />

        <motion.p
          className='max-w-[760px] text-[15px] leading-[1.2] text-secondary-foreground lg:text-base lg:leading-6'
          variants={ENTRANCE_RISE}
        >
          {intro}
        </motion.p>

        <SkillCompletionIndicators indicators={indicators} />
        <SkillCompletionLegend items={legendItems} />
        <SkillCompletionOverall overall={overall} />
        <SkillCompletionCompetencyList competencies={competencies} />
        <SkillReviewPractice review={review} />

        <motion.div className='flex lg:justify-end' variants={ENTRANCE_RISE}>
          <Link
            className='inline-flex min-h-11 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 lg:w-auto'
            params={goalParams}
            to={ROUTES.learningGoal}
          >
            Voltar ao Objetivo
          </Link>
        </motion.div>
      </MotionEntrance>
    </div>
  )
}
