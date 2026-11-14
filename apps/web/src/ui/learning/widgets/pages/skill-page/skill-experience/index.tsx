import { Link } from '@tanstack/react-router'
import { motion } from 'motion/react'

import type { SkillExperienceDetail } from '@/core/learning/skill-experience'
import { ENTRANCE_RISE, ENTRANCE_SECTION } from '@/constants/motion-variants'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { SkillCompetencyList } from '../skill-competency-list'
import { SkillEvaluationNotice } from '../skill-evaluation-notice'
import { SkillOverview } from '../skill-overview'
import { SkillRecommendationCard } from '../skill-recommendation'

export type SkillExperienceProps = {
  experience: SkillExperienceDetail
  isRetrying: boolean
  onRetryEvaluation: () => void
  retryFailed: boolean
  onRemove: () => void
}

export const SkillExperience = ({
  experience,
  isRetrying,
  onRetryEvaluation,
  retryFailed,
  onRemove,
}: SkillExperienceProps) => {
  return (
    <main className='w-full px-5 py-10 sm:px-10 lg:px-20'>
      <MotionEntrance className='flex w-full flex-col gap-6'>
        <motion.div variants={ENTRANCE_RISE}>
          <Link
            className='inline-flex min-h-[38px] items-center rounded-md px-3 py-2.5 text-base font-medium text-secondary-foreground transition-colors hover:text-foreground'
            params={{ goalId: experience.goalId }}
            to='/learning/goals/$goalId'
          >
            Voltar para o Objetivo
          </Link>
        </motion.div>

        <SkillOverview
          overallCoverageComplete={experience.overallCoverageComplete}
          overallResult={experience.overallResult}
          skillName={experience.skillName}
          skillStatus={experience.skillStatus}
          onRemove={onRemove}
        />

        {/* The flex column keeps the link stretched across the row, as it was
        before the entrance wrapper. */}
        <motion.div className='flex flex-col' variants={ENTRANCE_RISE}>
          <Link
            className='inline-flex min-h-11 items-center text-base font-semibold text-primary underline-offset-4 hover:underline'
            params={{ goalId: experience.goalId, skillId: experience.skillId }}
            to='/learning/goals/$goalId/skills/$skillId/diagnostic/result'
          >
            Ver diagnóstico consolidado
          </Link>
        </motion.div>

        {experience.evaluation ? (
          <motion.div variants={ENTRANCE_SECTION}>
            <SkillEvaluationNotice
              evaluation={experience.evaluation}
              isRetrying={isRetrying}
              onRetry={onRetryEvaluation}
              retryFailed={retryFailed}
            />
          </motion.div>
        ) : experience.recommendation ? (
          <motion.div variants={ENTRANCE_SECTION}>
            <SkillRecommendationCard
              goalId={experience.goalId}
              recommendation={experience.recommendation}
              skillId={experience.skillId}
            />
          </motion.div>
        ) : null}

        <SkillCompetencyList
          competencies={experience.competencies}
          focusCompetencyName={experience.focusCompetencyName}
          goalId={experience.goalId}
          skillId={experience.skillId}
        />
      </MotionEntrance>
    </main>
  )
}
