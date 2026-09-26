import { Link } from '@tanstack/react-router'

import {
  DIFFICULTY_LABELS,
  RECOMMENDATION_TYPE_LABELS,
  type SkillRecommendation,
} from '@/core/learning/skill-experience'

export type SkillRecommendationCardProps = {
  goalId: string
  recommendation: SkillRecommendation
  skillId: string
}

export const SkillRecommendationCard = ({
  goalId,
  recommendation,
  skillId,
}: SkillRecommendationCardProps) => {
  return (
    <section
      aria-labelledby='skill-recommendation-title'
      className='flex flex-col gap-3 rounded-[10px] bg-surface-alt p-[18px] sm:flex-row sm:items-center sm:justify-between sm:gap-4'
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <p className='flex flex-wrap items-center gap-2'>
          <span className='rounded-md bg-accent px-2 py-1 text-[11px] font-medium text-selo-text'>
            {DIFFICULTY_LABELS[recommendation.difficulty]}
          </span>
          <span className='rounded-md bg-muted px-2 py-1 text-[11px] font-medium text-secondary-foreground'>
            {RECOMMENDATION_TYPE_LABELS[recommendation.type]}
          </span>
        </p>
        <h2
          className='truncate text-[17px] font-medium text-foreground'
          id='skill-recommendation-title'
        >
          {recommendation.activityTitle}
        </h2>
      </div>

      <div className='flex w-full flex-col gap-2 sm:w-auto sm:shrink-0 sm:flex-row-reverse sm:gap-2.5'>
        <Link
          className='inline-flex min-h-[38px] items-center justify-center rounded-md bg-primary px-[18px] text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90'
          params={{
            activityId: recommendation.activityId,
            competencyId: recommendation.competencyId,
            goalId,
            skillId,
          }}
          to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId'
        >
          Continuar praticando
        </Link>
        <Link
          className='inline-flex min-h-[38px] items-center justify-center rounded-md border border-control-border px-[18px] text-sm font-semibold text-foreground transition-colors hover:bg-muted'
          params={{
            competencyId: recommendation.competencyId,
            goalId,
            skillId,
          }}
          to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
        >
          Escolher outra
        </Link>
      </div>
    </section>
  )
}
