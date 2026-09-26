import { Link } from '@tanstack/react-router'

import type { SkillExperienceDetail } from '@/core/learning/skill-experience'

import { SkillCompetencyList } from '../skill-competency-list'
import { SkillEvaluationNotice } from '../skill-evaluation-notice'
import { SkillOverview } from '../skill-overview'
import { SkillRecommendationCard } from '../skill-recommendation'

export type SkillExperienceProps = {
  experience: SkillExperienceDetail
  isRetrying: boolean
  onRetryEvaluation: () => void
  retryFailed: boolean
}

export const SkillExperience = ({
  experience,
  isRetrying,
  onRetryEvaluation,
  retryFailed,
}: SkillExperienceProps) => {
  return (
    <main className='flex w-full flex-col gap-6 px-5 py-10 sm:px-10 lg:px-20'>
      <div>
        <Link
          className='inline-flex min-h-[38px] items-center rounded-md px-3 py-2.5 text-sm font-medium text-secondary-foreground transition-colors hover:text-foreground'
          params={{ goalId: experience.goalId }}
          to='/learning/goals/$goalId'
        >
          Voltar para o Objetivo
        </Link>
      </div>

      <SkillOverview
        overallResult={experience.overallResult}
        skillName={experience.skillName}
        skillStatus={experience.skillStatus}
      />

      {experience.evaluation ? (
        <SkillEvaluationNotice
          evaluation={experience.evaluation}
          isRetrying={isRetrying}
          onRetry={onRetryEvaluation}
          retryFailed={retryFailed}
        />
      ) : experience.recommendation ? (
        <SkillRecommendationCard
          goalId={experience.goalId}
          recommendation={experience.recommendation}
          skillId={experience.skillId}
        />
      ) : null}

      <SkillCompetencyList
        competencies={experience.competencies}
        focusCompetencyName={experience.focusCompetencyName}
        goalId={experience.goalId}
        skillId={experience.skillId}
      />
    </main>
  )
}
